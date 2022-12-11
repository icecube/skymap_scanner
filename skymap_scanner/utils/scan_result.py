"""For encapsulating the results of an event scan in a single instance."""

import itertools as it
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import io
import pickle
from astropy.io import ascii
from functools import cached_property

import numpy as np
import matplotlib
from matplotlib import text
from matplotlib import pyplot as plt
import healpy
import meander

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

    def __init__(self, result: Dict[str, np.ndarray]):
        self.logger = logging.getLogger(__name__)
        self.result = result
        self.nsides = sorted([self.parse_nside(key) for key in self.result])
        self.logger.debug(f"Metadata for this result: {[self.result[_].dtype.metadata for _ in self.result]}")

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

    def has_metadata(self) -> bool:
        """ Check that the minimum metadata is set
        """
        for mk in "run_id event_id mjd event_type nside".split():
            for k in self.result:
                if self.result[k].dtype.metadata is None:
                    return False
                if mk not in self.result[k].dtype.metadata:
                    return False
        return True

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
    def format_nside(nside):
        return f"nside-{nside}"

    @staticmethod
    def parse_nside(key):
        return int(key.split("nside-")[1])

    @classmethod
    def from_nsides_dict(cls, nsides_dict: NSidesDict, **kwargs) -> "ScanResult":
        """Factory method for nsides_dict."""
        result = cls.load_pixels(nsides_dict, **kwargs)
        return cls(result)

    @classmethod
    def load_pixels(cls, nsides_dict: NSidesDict, **kwargs):
        logger = logging.getLogger(__name__)

        out = dict()
        for nside, pixel_dict in nsides_dict.items():
            _dtype = np.dtype(cls.PIXEL_TYPE, metadata=dict(nside=nside, **kwargs))
            n = len(pixel_dict)
            v = np.zeros(n, dtype=_dtype)

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
        return "_".join([str(nside) for nside in self.nsides])

    @classmethod
    def load(cls, filename) -> "ScanResult":
        npz = np.load(filename)
        result = dict()
        if "header" not in npz:
            for key in npz.keys():
                result[key] = npz[key]
        else:
            h = npz["header"]
            for v in h:
                key = cls.format_nside(v['nside'])
                _dtype = np.dtype(npz[key].dtype, metadata={k:value for k, value in zip(h.dtype.fields.keys(), v)})
                result[key] = np.array(list(npz[key]), dtype=_dtype)
        return cls(result=result)

    def save(self, event_id, output_path=None) -> Path:
        filename = event_id + "_" + self.get_nside_string() + ".npz"
        if output_path is not None:
            filename = output_path / Path(filename)
        try:
            metadata_dtype = np.dtype(
                [(k, type(v)) if not isinstance(v, str) else (k, f"U{len(v)}")
                 for k, v in next(iter(self.result.values())).dtype.metadata.items()],
                )
            h = np.array([tuple(self.result[k].dtype.metadata[mk] for mk in metadata_dtype.fields)
                           for k in self.result],
                         dtype=metadata_dtype)
            np.savez(filename, header=h, **self.result)
        except TypeError:
            np.savez(filename, **self.result)
        return Path(filename)

    """
    Querying
    """

    def llh(self, ra, dec):
        for nside in self.nsides[::-1]:
            grid_pix = healpy.ang2pix(nside, dec + np.pi/2., ra)
            _res = self.result[self.format_nside(nside)]
            llh = _res[_res['index']==grid_pix]['llh']
            if llh.size > 0:
                return llh

    @property
    def min_llh(self):
        return self.best_fit['llh']

    @cached_property
    def best_fit(self):
        _minllh = np.inf
        for k in self.result:
            _res = self.result[k]
            _min = _res['llh'].min()
            if _min < _minllh:
                _minllh = _min
                _bestfit = _res[_res['llh'].argmin()]
        return _bestfit

    @property
    def best_dir(self):
        minDec, minRA = healpy.pix2ang(self.best_fit.dtype.metadata['nside'], self.best_fit['index'])
        minDec = minDec - np.pi/2.
        return minRA, minDec

    """
    Plotting routines
    """

    def create_plot(self,
                    dosave=False,
                    dozoom=False,
                    log_func=None,
                    upload_func=None,
                    final_channels=None):
        from .plotting_tools import RaFormatter, DecFormatter
        from .icetrayless import create_event_id

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

        if self.has_metadata():
            run_id, event_id, event_type, mjd = [
                self.result[k].dtype.metadata[_] for _ in "run_id event_id event_type mjd".split()]
        else:
            self.logger.warn(f"Metadata doesn't seem to exist and will not be used for plotting.")
            run_id, event_id, event_type, mjd = [0]*4
        unique_id = f'{create_event_id(run_id, event_id)}_{self.get_nside_string()}'

        plot_title = f"Run: {run_id} Event {event_id}: Type: {event_type} MJD: {mjd}"

        plot_filename = f"{unique_id}.{'plot_zoomed.' if dozoom else ''}pdf"
        print(f"saving plot to {plot_filename}")

        nsides = self.nsides
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
        for nside in nsides:
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
        cmap = matplotlib.cm.plasma_r
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

        if dozoom:
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

    def create_plot_zoomed(self,
                           dosave=False,
                           log_func=None,
                           upload_func=None,
                           extra_ra=np.nan,
                           extra_dec=np.nan,
                           extra_radius=np.nan,
                           systematics=False,
                           plot_bounding_box=False,
                           plot_4fgl=False,
                           final_channels=None):
        """ Uses healpy to plot a map
        """
        from .plotting_tools import (hp_ticklabels,
                                     format_fits_header,
                                     plot_catalog)
        from .icetrayless import create_event_id

        if log_func is None:
            def log_func(x):
                print(x)

        if upload_func is None:
            def upload_func(file_buffer, name, title):
                pass

        if final_channels is None:
            final_channels=["#test_messaging"]

        def bounding_box(ra, dec, theta, phi):
            shift = ra-180

            ra_plus = np.max((np.degrees(phi)-shift)%360) - 180
            ra_minus = np.min((np.degrees(phi)-shift)%360) - 180
            dec_plus = (np.max(theta)-np.pi/2.)*180./np.pi - dec
            dec_minus = (np.min(theta)-np.pi/2.)*180./np.pi - dec
            return ra_plus, ra_minus, dec_plus, dec_minus

        y_inches = 3.85
        x_inches = 6.
        dpi = 1200.
        xsize = x_inches*dpi
        ysize = xsize/2.

        lonra=[-10.,10.]
        latra=[-10.,10.]

        for k in self.result:
            if "nside-" not in k:
                raise RuntimeError("\"nside\" not in result file..")

        if self.has_metadata():
            run_id, event_id, event_type, mjd = [
                self.result[k].dtype.metadata[_] for _ in "run_id event_id event_type mjd".split()]
        else:
            self.logger.warn(f"Metadata doesn't seem to exist and will not be used for plotting.")
            run_id, event_id, event_type, mjd = [0]*4
        unique_id = f'{create_event_id(run_id, event_id)}_{self.get_nside_string()}'

        plot_title = f"Run: {run_id} Event {event_id}: Type: {event_type} MJD: {mjd}"

        nsides = self.nsides
        print(f"available nsides: {nsides}")

        if systematics is not True:
            plot_filename = unique_id + ".plot_zoomed_wilks.pdf"
        else:
            plot_filename = unique_id + ".plot_zoomed.pdf"
        print("saving plot to {0}".format(plot_filename))

        nsides = self.nsides
        print(f"available nsides: {nsides}")

        grid_map = dict()
        max_nside = max(nsides)
        master_map = np.full(healpy.nside2npix(max_nside), np.nan)

        for nside in nsides:
            print("constructing map for nside {0}...".format(nside))
            npix = healpy.nside2npix(nside)

            map_data = self.result[f'nside-{nside}']
            pixels = map_data['index']
            values = map_data['llh']
            this_map = np.full(npix, np.nan)
            this_map[pixels] = values
            if nside < max_nside:
                this_map = healpy.ud_grade(this_map, max_nside)
            mask = np.logical_and(~np.isnan(this_map), np.isfinite(this_map))
            master_map[mask] = this_map[mask]

            for pixel_data in self.result[f"nside-{nside}"]:
                pixel = pixel_data['index']
                value = pixel_data['llh']
                if np.isfinite(value) and not np.isnan(value):
                    tmp_theta, tmp_phi = healpy.pix2ang(nside, pixel)
                    tmp_dec = tmp_theta - np.pi/2.
                    tmp_ra = tmp_phi
                    grid_map[(tmp_dec, tmp_ra)] = value
            print("done with map for nside {0}...".format(nside))

        grid_dec = []; grid_ra = []; grid_value = []

        for (dec, ra), value in grid_map.items():
            grid_dec.append(dec); grid_ra.append(ra)
            grid_value.append(value)
        grid_dec = np.asarray(grid_dec)
        grid_ra = np.asarray(grid_ra)
        grid_value = np.asarray(grid_value)

        sorting_indices = np.argsort(grid_value)
        grid_value = grid_value[sorting_indices]
        grid_dec = grid_dec[sorting_indices]
        grid_ra = grid_ra[sorting_indices]

        min_value = grid_value[0]
        minDec = grid_dec[0]
        minRA = grid_ra[0]

        print("min  RA:", minRA *180./np.pi, "deg,", minRA*12./np.pi, "hours")
        print("min dec:", minDec*180./np.pi, "deg")

        # renormalize
        grid_value = grid_value - min_value
        min_value = 0.

        # show 2 * delta_LLH 
        grid_value = grid_value * 2.

        # Do same for the healpy map
        master_map[np.isinf(master_map)] = np.nan
        master_map -= np.nanmin(master_map)
        master_map *= 2.

        print("preparing plot: {0}...".format(plot_filename))

        cmap = matplotlib.cm.plasma_r
        cmap.set_under('w')
        cmap.set_bad(alpha=1., color=(1.,0.,0.)) # make NaNs bright red

        # Calculate the contours
        if systematics:
            # from Pan-Starrs event 127852
            contour_levels = (np.array([22.2, 64.2])+min_value) # these are values determined from MC by Will on the TS (2*LLH)
            contour_labels = [r'50% (IC160427A syst.)', r'90% (IC160427A syst.)']
            contour_colors=['k', 'r']
        else:
            # # Wilk's
            contour_levels = (np.array([1.39, 4.61, 11.83, 28.74])+min_value)[:3]
            contour_labels = [r'50%', r'90%', r'3$\sigma$', r'5$\sigma$'][:3]
            contour_colors=['k', 'r', 'g', 'b'][:3]

        sample_points = np.array([grid_dec + np.pi/2., grid_ra]).T
        # Call meander module to find contours
        contours_by_level = meander.spherical_contours(sample_points,
            grid_value, contour_levels
            )
        # Check for RA values that are out of bounds
        for level in contours_by_level:
            for contour in level:
                contour.T[1] = np.where(contour.T[1] < 0., 
                    contour.T[1] + 2.*np.pi, contour.T[1]
                    )


        # Find the rough extent of the contours to bound the plot
        contours = contours_by_level[-1]
        ra = minRA * 180./np.pi
        dec = minDec * 180./np.pi
        theta, phi = np.concatenate(contours_by_level[-1]).T
        ra_plus, ra_minus, dec_plus, dec_minus = bounding_box(ra, dec, theta, phi)
        ra_bound = min(15, max(3, max(-ra_minus, ra_plus)))
        dec_bound = min(15, max(2, max(-dec_minus, dec_plus)))
        lonra = [-ra_bound, ra_bound]
        latra = [-dec_bound, dec_bound]

        #Begin the figure 
        plt.clf()
        # Rotate into healpy coordinates
        lon, lat = np.degrees(minRA), -np.degrees(minDec)
        healpy.cartview(map=master_map, title=plot_title,
            min=0., #min 2DeltaLLH value for colorscale
            max=40., #max 2DeltaLLH value for colorscale
            rot=(lon,lat,0.), cmap=cmap, hold=True,
            cbar=None, lonra=lonra, latra=latra,
            unit=r"$-2 \Delta \ln (L)$",
            )
        plt.gca().invert_yaxis()

        fig = plt.gcf()
        ax = plt.gca()
        image = ax.get_images()[0]
        # Place colorbar by hand
        cb = fig.colorbar(image, ax=ax, orientation='horizontal', aspect=50)
        cb.ax.xaxis.set_label_text(r"$-2 \Delta \ln (L)$")

        # Plot the best-fit location
        # This requires some more coordinate transformations
        healpy.projplot(minDec + np.pi/2., minRA, 
            '*', ms=5, label=r'scan best fit', color='black', zorder=2)

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

        # Plot the contours
        for contour_level, contour_label, contour_color, contours in zip(contour_levels, 
            contour_labels, contour_colors, contours_by_level):
            contour_area = 0 
            for contour in contours:
                contour_area += area((contour-ra+np.pi/2)%np.pi)
            contour_area = abs(contour_area)
            contour_area *= (180.*180.)/(np.pi*np.pi) # convert to square-degrees
            contour_label = contour_label + ' - area: {0:.2f} sqdeg'.format(
                contour_area)
            first = True
            for contour in contours:
                theta, phi = contour.T
                if first:
                    healpy.projplot(theta, phi, linewidth=2, c=contour_color, 
                        label=contour_label)
                else:
                    healpy.projplot(theta, phi, linewidth=2, c=contour_color)
                first = False

        # Add some grid lines
        healpy.graticule(dpar=2, dmer=2, force=True) 

        # Set some axis limits
        lower_ra = minRA + np.radians(lonra[0])
        upper_ra = minRA + np.radians(lonra[1])
        lower_dec = minDec + np.radians(latra[0])
        upper_dec = minDec + np.radians(latra[1])

        lower_lon = np.degrees(lower_ra)
        upper_lon = np.degrees(upper_ra)
        tmp_lower_lat = -1.*np.degrees(lower_dec)
        tmp_upper_lat = -1.*np.degrees(upper_dec)
        lower_lat = min(tmp_lower_lat, tmp_upper_lat)
        upper_lat = max(tmp_lower_lat, tmp_upper_lat)

        # Label the axes
        hp_ticklabels(zoom=True, lonra=lonra, latra=latra, 
            rot=(lon,lat,0), 
            bounds=(lower_lon, upper_lon, lower_lat, upper_lat))

        if plot_4fgl:
            # Overlay 4FGL sources
            plot_catalog(master_map, cmap, lower_ra, upper_ra, lower_dec, upper_dec)

        # Approximate contours as rectangles
        ra = minRA * 180./np.pi
        dec = minDec * 180./np.pi
        for l, contours in enumerate(contours_by_level[:2]):
            ra_plus = None
            theta, phi = np.concatenate(contours).T
            ra_plus, ra_minus, dec_plus, dec_minus = bounding_box(ra, dec, theta, phi)
            contain_txt = "Approximating the {0}% error region as a rectangle, we get:".format(["50", "90"][l]) + " \n" + \
                          "\t RA = {0:.2f} + {1:.2f} - {2:.2f}".format(
                              ra, ra_plus, np.abs(ra_minus)) + " \n" + \
                          "\t Dec = {0:.2f} + {1:.2f} - {2:.2f}".format(
                              dec, dec_plus, np.abs(dec_minus))                
            log_func(contain_txt)
        if plot_bounding_box:
            bounding_ras = []; bounding_decs = []
            # lower bound
            bounding_ras.extend(list(np.linspace(ra+ra_minus, 
                ra+ra_plus, 10)))
            bounding_decs.extend([dec+dec_minus]*10)
            # right bound
            bounding_ras.extend([ra+ra_plus]*10)
            bounding_decs.extend(list(np.linspace(dec+dec_minus,
                dec+dec_plus, 10)))
            # upper bound
            bounding_ras.extend(list(np.linspace(ra+ra_plus,
                ra+ra_minus, 10)))
            bounding_decs.extend([dec+dec_plus]*10)
            # left bound
            bounding_ras.extend([ra+ra_minus]*10)
            bounding_decs.extend(list(np.linspace(dec+dec_plus,
                dec+dec_minus,10)))
            # join end to beginning
            bounding_ras.append(bounding_ras[0])
            bounding_decs.append(bounding_decs[0])
            bounding_ras = np.asarray(bounding_ras)
            bounding_decs = np.asarray(bounding_decs)
            bounding_phi = np.radians(bounding_ras)
            bounding_theta = np.radians(bounding_decs) + np.pi/2.
            bounding_contour = np.array([bounding_theta, bounding_phi])
            bounding_contour_area = 0.
            bounding_contour_area = area(bounding_contour.T)
            bounding_contour_area *= (180.*180.)/(np.pi*np.pi) # convert to square-degrees
            contour_label = r'90% Bounding rectangle' + ' - area: {0:.2f} sqdeg'.format(
                bounding_contour_area)
            healpy.projplot(bounding_theta, bounding_phi, linewidth=0.75, 
                c='r', linestyle='dashed', label=contour_label)

        # Output contours in RA, dec instead of theta, phi
        saving_contours = []
        for contours in contours_by_level:
            saving_contours.append([])
            for contours in contours:
                saving_contours[-1].append([])
                theta, phi = contour.T
                ras = phi
                decs = theta - np.pi/2.
                for tmp_ra, tmp_dec in zip(ras, decs):
                    saving_contours[-1][-1].append([tmp_ra, tmp_dec])

        # Save the individual contours, send messages
        for i, val in enumerate(["50", "90"]):
            ras = list(np.asarray(saving_contours[i][0]).T[0])
            decs = list(np.asarray(saving_contours[i][0]).T[1])
            tab = {"ra (rad)": ras, "dec (rad)": decs}
            savename = unique_id + ".contour_" + val + ".txt"
            try:
                ascii.write(tab, savename, overwrite=True)
                print("Dumping to", savename)
                for i, ch in enumerate(final_channels):
                    output = io.StringIO()
                    #output = str.encode(savename)
                    if dosave:
                        ascii.write(tab, output, overwrite=True)
                    output.seek(0) 
                    print(upload_func(output, savename, savename))
                    output.truncate(0) 
                    del output
            except OSError:
                log_func("Memory Error prevented contours from being written")

        uncertainty = [(ra_minus, ra_plus), (dec_minus, dec_plus)]
        fits_header = format_fits_header((run_id, event_id, event_type), 0, 
            np.degrees(minRA), np.degrees(minDec), uncertainty,
           )
        mmap_nside = healpy.get_nside(master_map)

        # Pixel numbers as is gives a map that is reflected
        # about the equator. This is all deal with self-consistently
        # here but we need to correct before outputting a fits file
        def fixpixnumber(nside,pixels):
            th_o, phi_o = healpy.pix2ang(nside, pixels)
            dec_o = th_o - np.pi/2
            th_fixed = np.pi/2 - dec_o 
            pix_fixed = healpy.ang2pix(nside, th_fixed, phi_o)
            return pix_fixed
        pixels = np.arange(len(master_map))
        nside = healpy.get_nside(master_map)
        new_pixels = fixpixnumber(nside, pixels)
        equatorial_map = master_map[new_pixels]

        # Plot the original online reconstruction location
        if np.sum(np.isnan([extra_ra, extra_dec, extra_radius])) == 0:

            def circular_contour(ra, dec, sigma, nside):
                """For plotting circular contours on skymaps
                ra, dec, sigma all expected in radians
                """
                dec = np.pi/2. - dec
                sigma = np.rad2deg(sigma)
                delta, step, bins = 0, 0, 0
                delta= sigma/180.0*np.pi
                step = 1./np.sin(delta)/10.
                bins = int(360./step)
                Theta = np.zeros(bins+1, dtype=np.double)
                Phi = np.zeros(bins+1, dtype=np.double)
                # define the contour
                for j in range(0,bins) :
                    phi = j*step/180.*np.pi
                    vx = np.cos(phi)*np.sin(ra)*np.sin(delta) + np.cos(ra)*(np.cos(delta)*np.sin(dec) + np.cos(dec)*np.sin(delta)*np.sin(phi))
                    vy = np.cos(delta)*np.sin(dec)*np.sin(ra) + np.sin(delta)*(-np.cos(ra)*np.cos(phi) + np.cos(dec)*np.sin(ra)*np.sin(phi))
                    vz = np.cos(dec)*np.cos(delta) - np.sin(dec)*np.sin(delta)*np.sin(phi)
                    idx = healpy.vec2pix(nside, vx, vy, vz)
                    DEC, RA = healpy.pix2ang(nside, idx)
                    Theta[j] = DEC
                    Phi[j] = RA
                Theta[bins] = Theta[0]
                Phi[bins] = Phi[0]
                return Theta, Phi

            # dist = angular_distance(minRA, minDec, extra_ra * np.pi/180., extra_dec * np.pi/180.)
            # print("Millipede best fit is", dist /(np.pi * extra_radius/(1.177 * 180.)), "sigma from reported best fit")
        

            extra_ra_rad = np.radians(extra_ra)
            extra_dec_rad = np.radians(extra_dec)
            extra_radius_rad = np.radians(extra_radius)
            extra_lon = extra_ra_rad
            extra_lat = -extra_dec_rad

            healpy.projscatter(np.degrees(extra_lon), np.degrees(extra_lat),
                lonlat=True, c='m', marker='x', s=20, label=r'Reported online (50%, 90%)')
            for cont_lev, cont_scale, cont_col, cont_sty in zip(['50', '90.'], 
                    [1., 2.1459/1.177], ['m', 'm'], ['-', '--']):
                spline_contour = circular_contour(extra_ra_rad, extra_dec_rad,
                    extra_radius_rad*cont_scale, healpy.get_nside(master_map))
                spline_lon = spline_contour[1]
                spline_lat = -1.*(np.pi/2. - spline_contour[0])
                healpy.projplot(np.degrees(spline_lon), np.degrees(spline_lat), 
                    lonlat=True, linewidth=2., color=cont_col, 
                    linestyle=cont_sty)

        plt.legend(fontsize=6, loc="lower left")

        # For vertical events, calculate the area with the number of pixels
        # In the healpy map   
        for lev in contour_levels[-1:]:
            area_per_pix = healpy.nside2pixarea(healpy.get_nside(master_map))
            num_pixs = np.count_nonzero(master_map[~np.isnan(master_map)] < lev)
            healpy_area = num_pixs * area_per_pix * (180./np.pi)**2.
        print("Contour Area (90%):", contour_area, "degrees (cartesian)", 
            healpy_area, "degrees (scaled)")

        if dosave:
            # Dump the whole contour
            path = unique_id + ".contour.pkl"
            print("Saving contour to", path)
            with open(path, "wb") as f:
                pickle.dump(saving_contours, f)

            healpy.write_map(f"{unique_id}.skymap_nside_{mmap_nside}.fits.gz",
                equatorial_map, coord = 'C', column_names = ['2LLH'],
                extra_header = fits_header, overwrite=True)

            # Save the figure
            print("saving: {0}...".format(plot_filename))
            #ax.invert_xaxis()
            fig.savefig(plot_filename, dpi=dpi, transparent=True)

        print("done.")

        if systematics is True:
            title = "Millipede contour, assuming IC160427A systematics:"
        else:
            title = "Millipede contour, assuming Wilk's Theorum:"

        for i, ch in enumerate(final_channels):
            imgdata = io.BytesIO()
            fig.savefig(imgdata, format='png', dpi=600, transparent=True)
            imgdata.seek(0)

            savename = plot_filename[:-4] + ".png"
            print(savename)
            # config.slack_channel=ch
            upload_func(imgdata, savename, title)

        plt.close()
        return imgdata
