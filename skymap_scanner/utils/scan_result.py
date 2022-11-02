"""For encapsulating the results of an event scan in a single instance."""

import itertools as it
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import io

import numpy as np

from .pixelreco import NSidesDict, PixelReco


class InvalidPixelValueError(Exception):
    """Raised when a pixel-value is illegal."""


class ScanResult:
    """This class parses a nsides_dict and stores the relevant numeric result
    of the scan. Ideally it should serve as the basic data structure for
    plotting / processing / transmission of the scan result.

    nsides_dict is a dictionary keyed by 'nside' values for which a scan
    result is available (e.g. 8, 64, 512), see `pixelreco.NSidesDict`.
    The scan result is a dictionary:
    - i (pixel index, integer) ->
        'frame', 'llh', 'recoLossesInside', 'recoLossesTotal'

    The numeric values of interest are 'llh', 'recoLossesInside',
    'recoLossesTotal'. The pixel indices in the input dictionary are in
    general unsorted (python dict are unsorted by design) and are
    incomplete (since fine-grained scans only cover a portion of the
    HEALPIX area). The class stores the each result in a np
    structured array sorted by the pixel index, which is stored in a
    dedicated field.

    TODO: implement FITS output.
    """

    PIXEL_TYPE = np.dtype(
        [("index", int), ("llh", float), ("E_in", float), ("E_tot", float)]
    )
    ATOL = 1.0e-8  # 1.0e-8 is the default used by np.isclose()

    def __init__(self, result: Dict[str, np.ndarray], event_id: str=''):
        self.logger = logging.getLogger(__name__)
        self.result = result
        self.event_id = event_id

        # bookkeeping for comparing values
        self.require_close = {  # w/ rtol values
            # any field not here is assumed to require '==' for comparison
            "llh": 1e-4,
            "E_in": 1e-2,
            "E_tot": 1e-2,
        }
        self.cannot_be_zero_fields = [
            # if field's val is 0, then all the pixel's numerical datapoints are "isclose"
            "E_in",
            "E_tot",
        ]

    """
    Comparison operators and methods
    """

    def __eq__(self, other: object) -> bool:
        """Are the two instance's result lists strictly equal?"""
        if not isinstance(other, ScanResult):
            return False
        if self.result.keys() != other.result.keys():
            return False
        # NOTE: will return false if NaN are present
        # np.array_equal() supports `equal_nan` option only from version 1.19
        return all(
            np.array_equal(self.result[nside], other.result[nside])
            for nside in self.result
        )

    def is_close_datapoint(
        self, s_val: float, o_val: float, field: str, equal_nan: bool
    ) -> Tuple[float, bool]:
        """Get the diff float-value and test truth-value for the 2 pixel
        datapoints."""
        if field not in self.require_close:
            raise ValueError(
                f"Datapoint field ({field}) cannot be compared by "
                f"'is_close_datapoint()', must use '=='"
            )
        if field in self.cannot_be_zero_fields and (s_val == 0.0 or o_val == 0.0):
            raise InvalidPixelValueError(f"field={field}, values={(s_val, o_val)}")
        try:
            rdiff = (abs(s_val - o_val) - self.ATOL) / abs(o_val)  # used by np.isclose
        except ZeroDivisionError:
            rdiff = float("inf")
        return (
            rdiff,
            bool(
                np.isclose(
                    s_val,
                    o_val,
                    equal_nan=equal_nan,
                    rtol=self.require_close[field],
                    atol=self.ATOL,
                )
            ),
        )

    def diff_pixel_data(
        self,
        sre_pix: np.ndarray,
        ore_pix: np.ndarray,
        equal_nan: bool,
        do_disqualify_zero_energy_pixels: bool,  # TODO: remove?
    ) -> Tuple[List[float], List[bool]]:
        """Get the diff float-values and test truth-values for the 2 pixel-
        data.

        The datapoints are compared face-to-face (zipped).

        If `do_disqualify_zero_energy_pixels=True` there's an
        invalid datapoint value in either array, all "require close"
        datapoints are considered (vacuously) close enough. # TODO: remove?
        """
        diff_vals = []
        test_vals = []

        # is one of the pixel-datapoints is "so bad" it has
        # disqualified all the other "require_close" datapoints?
        is_pixel_disqualified = False  # TODO: remove?
        if do_disqualify_zero_energy_pixels:  # TODO: remove?
            is_pixel_disqualified = any(
                sre_pix[self.PIXEL_TYPE.names.index(f)] == 0.0
                or ore_pix[self.PIXEL_TYPE.names.index(f)] == 0.0
                for f in self.cannot_be_zero_fields
            )

        for s_val, o_val, field in zip(sre_pix, ore_pix, self.PIXEL_TYPE.names):
            s_val, o_val = float(s_val), float(o_val)

            # CASE 1: a disqualified-pixel "require close" datapoint
            if field in self.require_close and is_pixel_disqualified:
                diff, test = float("nan"), True  # vacuously true
            # CASE 2: a "require close" datapoint (not disqualified-pixel)
            elif field in self.require_close:
                try:
                    diff, test = self.is_close_datapoint(s_val, o_val, field, equal_nan)
                except InvalidPixelValueError:
                    diff, test = float("nan"), True
            # CASE 3: a "require equal" datapoint
            else:
                diff, test = s_val - o_val, s_val == o_val

            diff_vals.append(diff)
            test_vals.append(test)

        return diff_vals, test_vals

    def is_close(
        self,
        other: "ScanResult",
        equal_nan: bool = True,
        dump_json_diff: Optional[Path] = None,
        do_disqualify_zero_energy_pixels: bool = False,  # TODO: remove?
    ) -> bool:
        """Checks if two results are close by requiring strict equality on
        pixel indices and close condition on numeric results.

        Optionally, pass a `Path` for `dump_json_diff` to get a json
        file containing every diff at the pixel-data level.
        """
        close: Dict[str, bool] = {}  # one bool for each nside value
        diffs: Dict[str, list] = {}  # (~4x size of self.results) w/ per-pixel info

        # now check individual nside-iterations
        for nside in sorted(self.result.keys() & other.result.keys(), reverse=True):
            self.logger.info(f"Comparing for nside={nside}")

            # Q: why aren't we using np.array_equal and np.allclose?
            # A: we want detailed pixel-level diffs w/out repeating detailed code

            # zip-iterate each pixel-data
            nside_diffs = []
            for sre_pix, ore_pix in it.zip_longest(
                self.result.get(nside, []),  # empty-list -> fillvalue
                other.result.get(nside, []),  # empty-list -> fillvalue
                fillvalue=np.full((len(self.PIXEL_TYPE.names),), np.nan),  # 1 vector
            ):
                diff_vals, test_vals = self.diff_pixel_data(
                    sre_pix, ore_pix, equal_nan, do_disqualify_zero_energy_pixels
                )
                pix_diff = [
                    tuple(sre_pix.tolist()),
                    tuple(ore_pix.tolist()),
                    tuple(diff_vals),  # diff float-value
                    tuple(test_vals),  # test truth-value
                ]
                for vals in pix_diff:
                    self.logger.debug(f"{nside}: {vals}")
                nside_diffs.append(pix_diff)

            if dump_json_diff:  # can be a lot of data, so only save it if we're dumping
                diffs[nside] = nside_diffs

            # aggregate test-truth values
            nside_equal = {
                field: all(
                    d[3][self.PIXEL_TYPE.names.index(field)] for d in nside_diffs
                )
                for field in set(self.PIXEL_TYPE.names) - set(self.require_close)
            }
            nside_close = {
                field: all(
                    d[3][self.PIXEL_TYPE.names.index(field)] for d in nside_diffs
                )
                for field in self.require_close
            }
            close[nside] = all(nside_equal.values()) and all(nside_close.values())

            # log results (test-truth values)
            if not all(nside_equal.values()):
                self.logger.info(f"Mismatched pixel indices for nside={nside}")
            if not all(nside_close.values()):
                self.logger.info(f"Mismatched numerical results for nside={nside}")
                self.logger.debug(f"{nside_close}")

        # finish up
        self.logger.info(f"Comparison result: {close}")

        if dump_json_diff:
            with open(dump_json_diff, "w") as f:
                self.logger.info(f"Writing diff to {dump_json_diff}...")
                json.dump(diffs, f, indent=3)

        return all(close.values())

    """
    Auxiliary methods
    """
    @staticmethod
    def parse_event_id(event_id_string):
        parts = event_id_string.split('.')
        if len(parts) != 3:
            raise RuntimeError("event ID must have 3 parts separated by '.'")

        if not parts[0].startswith("run"):
            raise RuntimeError("event ID run part does not start with \"run\"")
        if not parts[1].startswith("evt"):
            raise RuntimeError("event ID event part does not start with \"evt\"")

        run = int(parts[0][3:])
        event = int(parts[1][3:])
        evt_type = parts[2]
        return (run, event, evt_type)

    @staticmethod
    def format_nside(nside):
        return f"nside-{nside}"

    @staticmethod
    def parse_nside(key):
        return int(key.split("nside-")[1])

    @classmethod
    def from_nsides_dict(cls, nsides_dict: NSidesDict) -> "ScanResult":
        """Factory method for nsides_dict."""
        result = cls.load_pixels(nsides_dict)
        return cls(result)

    @classmethod
    def load_pixels(cls, nsides_dict: NSidesDict):
        logger = logging.getLogger(__name__)

        out = dict()

        for nside, pixel_dict in nsides_dict.items():
            n = len(pixel_dict)
            v = np.zeros(n, dtype=cls.PIXEL_TYPE)

            logger.info(f"nside {nside} has {n} pixels / {12 * nside**2} total.")

            for i, (pixel_id, pixreco) in enumerate(sorted(pixel_dict.items())):
                if (
                    not isinstance(pixreco, PixelReco)
                    or nside != pixreco.nside
                    or pixel_id != pixreco.pixel
                ):
                    msg = f"Invalid {PixelReco} for {(nside,pixel_id)}: {pixreco}"
                    logging.error(msg)
                    raise ValueError(msg)
                v[i] = (
                    pixreco.pixel,  # index
                    pixreco.llh,  # llh
                    pixreco.reco_losses_inside,  # E_in
                    pixreco.reco_losses_total,  # E_tot
                )
            key = cls.format_nside(nside)
            out[key] = v

        return out

    """ 
    np input / output
    """

    def get_nside_string(self):
        """Returns a string string listing the nside values to be included in
        the output filename."""
        # keys have a 'nside-NNN' format but we just want to extract the nside values to build the string
        # parsing back and forth numbers to strings is not the most elegant choice but works for now
        # TODO: possibly better to use integer values as keys in self.result
        nsides = sorted([self.parse_nside(key) for key in self.result])
        return "_".join([str(nside) for nside in nsides])

    @classmethod
    def load(cls, filename) -> "ScanResult":
        npz = np.load(filename)
        result = dict()
        for key in npz.keys():
            result[key] = npz[key]
        return cls(result=result, event_id=Path(filename).stem)

    def save(self, event_id, output_path=None) -> Path:
        filename = event_id + "_" + self.get_nside_string() + ".npz"
        if output_path is not None:
            filename = output_path / Path(filename)
        np.savez(filename, **self.result)
        return Path(filename)

    def create_plot(self,
                    dosave=False,
                    dozoom=False,
                    log_func=None,
                    upload_func=None,
                    final_channels=None):
        import matplotlib
        from matplotlib import text
        from .plotting_tools import hp_ticklabels, RaFormatter, DecFormatter, AstroMollweideAxes
        import healpy
        if log_func is None:
            def log_func(x):
                print(x)

        if upload_func is None:
            def upload_func(file_buffer, name, title):
                pass

        if final_channels is None:
            final_channels=["#test_messaging"]
        y_inches = 3.85
        x_inches = 6
        dpi = 150 if not dozoom else 1200
        xsize = x_inches*dpi
        ysize = xsize//2

        lonra=[-10.,10.]
        latra=[-10.,10.]

        for k in self.result:
            if "nside-" not in k:
                raise RuntimeError("\"nside\" not in result file..")

        run_id, event_id, event_type = self.parse_event_id(self.event_id)

        # mjd = get_event_mjd(state_dict)

        plot_title = f"Run: {run_id} Event {event_id}: Type: {event_type} MJD: TODO"

        plot_filename = f"{self.event_id}.{'plot_zoomed.' if dozoom else ''}pdf"
        print(f"saving plot to {plot_filename}")

        nsides = [self.parse_nside(_) for _ in self.result]
        print(f"available nsides: {nsides}")

        maps = []
        min_value = np.nan
        max_value = np.nan
        minRA=0.
        minDec=0.

        # theta = np.linspace(np.pi, 0., ysize)
        dec = np.linspace(-np.pi/2., np.pi/2., ysize)

        # phi   = np.linspace(0., 2.*np.pi, xsize)
        ra = np.linspace(0., 2.*np.pi, xsize)

        # project the map to a rectangular matrix xsize x ysize
        RA, DEC = np.meshgrid(ra, dec)

        grid_map = None

        grid_pix = None

        # now plot maps above each other
        for nside in sorted(nsides):
            print(("constructing map for nside {0}...".format(nside)))
            # grid_pix = healpy.ang2pix(nside, THETA, PHI)
            grid_pix = healpy.ang2pix(nside, DEC + np.pi/2., RA)
            this_map = np.ones(healpy.nside2npix(nside))*np.inf

            for pixel_data in self.result[f'nside-{nside}']:
                pixel = pixel_data['index']
                # show 2*delta_LLH
                value = 2*pixel_data['llh']
                if np.isfinite(value):
                    if np.isnan(min_value) or value < min_value:
                        minDec, minRA = healpy.pix2ang(nside, pixel)
                        minDec = minDec - np.pi/2.
                        min_value = value
                    if np.isnan(max_value) or value > max_value:
                        max_value = value
                this_map[pixel] = value

            if grid_map is None:
                grid_map = this_map[grid_pix]
            else:
                grid_map = np.where( np.isfinite(this_map[grid_pix]), this_map[grid_pix], grid_map)

            del this_map

            print(("done with map for nside {0}...".format(nside)))

        # clean up
        if grid_pix is not None:
            del grid_pix

        if grid_map is None:
            # create an "empty" map if there are no pixels at all
            grid_pix = healpy.ang2pix(8, DEC + np.pi/2., RA)
            this_map = np.ones(healpy.nside2npix(8))*np.inf
            grid_map = this_map[grid_pix]
            del this_map
            del grid_pix

        print("min  RA:", minRA *180./np.pi, "deg,", minRA*12./np.pi, "hours")
        print("min dec:", minDec*180./np.pi, "deg")

        # renormalize
        if dozoom:
            grid_map = grid_map - min_value
            # max_value = max_value - min_value
            min_value = 0.
            max_value = 50

        grid_map = np.ma.masked_invalid(grid_map)

        print(f"preparing plot: {plot_filename}...")

        # the color map to use
        cmap = matplotlib.cm.viridis_r
        cmap.set_under(alpha=0.) # make underflows transparent
        cmap.set_bad(alpha=1., color=(1.,0.,0.)) # make NaNs bright red

        # prepare the figure canvas
        fig = matplotlib.pyplot.figure(figsize=[x_inches,y_inches])
        if dozoom:
            ax = fig.add_subplot(111) #,projection='cartesian')
        else:
            cmap.set_over(alpha=0.)  # make underflows transparent
            ax = fig.add_subplot(111,projection='astro mollweide')

        # rasterized makes the map bitmap while the labels remain vectorial
        # flip longitude to the astro convention
        image = ax.pcolormesh(ra, dec, grid_map, vmin=min_value, vmax=max_value, rasterized=True, cmap=cmap)
        # ax.set_xlim(np.pi, -np.pi)

        # Use Green's theorem to compute the area
        # enclosed by the given contour.
        def area(vs):
            a = 0
            x0,y0 = vs[0]
            for [x1,y1] in vs[1:]:
                dx = x1-x0
                dy = y1-y0
                a += 0.5*(y0*dx - x0*dy)
                x0 = x1
                y0 = y1
            return a

        contour_levels = (np.array([1.39, 4.61, 11.83, 28.74])+min_value)[:2]
        contour_labels = [r'50%', r'90%', r'3$\sigma$', r'5$\sigma$'][:2]
        contour_colors=['k', 'r', 'g', 'b'][:2]
        leg_element=[]
        cs_collections = []
        for level, color in zip(contour_levels, contour_colors):
            CS = ax.contour(ra, dec, grid_map, levels=[level], colors=[color])
            cs_collections.append(CS.collections[0])
            e, _ = CS.legend_elements()
            leg_element.append(e[0])

        if not dozoom:
            # graticule
            ax.set_longitude_grid(30)
            ax.set_latitude_grid(30)
            cb = fig.colorbar(image, orientation='horizontal', shrink=.6, pad=0.05, ticks=[min_value, max_value])
            cb.ax.xaxis.set_label_text(r"$-2 \ln(L)$")
        else:
            ax.set_xlabel('right ascension')
            ax.set_ylabel('declination')
            cb = fig.colorbar(image, orientation='horizontal', shrink=.6, pad=0.13)
            cb.ax.xaxis.set_label_text(r"$-2 \Delta \ln (L)$")

            leg_labels = []
            for i in range(len(contour_labels)):
                vs = cs_collections[i].get_paths()[0].vertices
                # Compute area enclosed by vertices.
                a = area(vs) # will be in square-radians
                a = a*(180.*180.)/(np.pi*np.pi) # convert to square-degrees

                leg_labels.append(f'{contour_labels[i]} - area: {a:.2f}sqdeg')

            ax.scatter(minRA, minDec, s=20, marker='*', color='black', label=r'scan best-fit', zorder=2)
            ax.legend(leg_element, leg_labels, loc='lower right', fontsize=8, scatterpoints=1, ncol=2)

            print("Contour Area (90%):", a, "degrees (cartesian)", a*np.cos(minDec)**2, "degrees (scaled)")
            x_width = 1.6 * np.sqrt(a)

            if np.isnan(x_width):
                x_width = 1.6*(max(CS.allsegs[i][0][:,0]) - min(CS.allsegs[i][0][:,0]))
            print(x_width)
            y_width = 0.5 * x_width

            lower_x = max(minRA  - x_width*np.pi/180., 0.)
            upper_x = min(minRA  + x_width*np.pi/180., 2 * np.pi)
            lower_y = max(minDec -y_width*np.pi/180., -np.pi/2.)
            upper_y = min(minDec + y_width*np.pi/180., np.pi/2.) 

            ax.set_xlim( [lower_x, upper_x][::-1])
            ax.set_ylim( [lower_y, upper_y])

            ax.xaxis.set_major_formatter(DecFormatter())
            ax.yaxis.set_major_formatter(DecFormatter())

            factor = 0.25*(np.pi/180.)
            while (upper_x - lower_x)/factor > 6:
                 factor *= 2.
            tick_label_grid = factor

            ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=tick_label_grid))
            ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=tick_label_grid))

        # cb.ax.xaxis.labelpad = -8
        # workaround for issue with viewers, see colorbar docstring
        cb.solids.set_edgecolor("face")

        ax.set_aspect('equal')
        ax.tick_params(axis='x', labelsize=10)
        ax.tick_params(axis='y', labelsize=10)

        # show the grid
        ax.grid(True, color='k', alpha=0.5)

        from matplotlib import patheffects
        # Otherwise, add the path effects.
        effects = [patheffects.withStroke(linewidth=1.1, foreground='w')]
        for artist in ax.findobj(text.Text):
            artist.set_path_effects(effects)

        # remove white space around figure
        spacing = 0.01
        if not dozoom:
            fig.subplots_adjust(bottom=spacing, top=1.-spacing, left=spacing+0.04, right=1.-spacing)
        else:
            fig.subplots_adjust(bottom=spacing, top=0.92-spacing, left=spacing+0.1, right=1.-spacing)

        # set the title
        fig.suptitle(plot_title)

        if dosave:
            print(f"saving: {plot_filename}...")

            fig.savefig(plot_filename, dpi=dpi, transparent=True)

        # use io.BytesIO to save this into a memory buffer
        imgdata = io.BytesIO()
        fig.savefig(imgdata, format='png', dpi=dpi, transparent=True)
        imgdata.seek(0)

        print("done.")

        return imgdata
