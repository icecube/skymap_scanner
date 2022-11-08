"""For encapsulating the results of an event scan in a single instance."""

import itertools as it
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    HEALPIX area). The class stores the each result in a numpy
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
        # numpy.array_equal() supports `equal_nan` option only from version 1.19
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
    def format_nside(nside):
        return f"nside-{nside}"

    @staticmethod
    def parse_nside(key):
        return int(key.split("nside-")[1])

    @classmethod
    def from_nsides_dict(cls, nsides_dict: NSidesDict,
                         run_id: Optional[int] = None,
                         event_id: Optional[int] = None,
                         mjd: Optional[float] = None) -> "ScanResult":
        """Factory method for nsides_dict."""
        result = cls.load_pixels(nsides_dict, run_id, event_id, mjd)
        return cls(result)

    @classmethod
    def load_pixels(cls, nsides_dict: NSidesDict,
                    run_id: Optional[int] = None,
                    event_id: Optional[int] = None,
                    mjd: Optional[float] = None):
        logger = logging.getLogger(__name__)

        out = dict()
        for nside, pixel_dict in nsides_dict.items():
            _dtype = np.dtype(cls.PIXEL_TYPE, metadata={"run_id": run_id,
                                                        "event_id": event_id,
                                                        "mjd": mjd,
                                                        "nside": nside})
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
    numpy input / output
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
            metadata_type = np.dtype(
                [("run_id", int), ("event_id", int), ("mjd", float), ("nside", int)],
                )
            h = np.array([(self.result[k].dtype.metadata["run_id"],
                           self.result[k].dtype.metadata["event_id"],
                           self.result[k].dtype.metadata["mjd"],
                           self.result[k].dtype.metadata["nside"]) for k in self.result],
                         dtype=metadata_type)
            np.savez(filename, header=h, **self.result)
        except TypeError:
            np.savez(filename, **self.result)
        return Path(filename)
