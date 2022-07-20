"""For encapsulating the results of an event scan in a single instance."""

import itertools as it
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

ATOL = 1.0e-8  # 1.0e-8 is the default used by np.isclose()


class ScanResult:
    """
    This class parses a nsides_dict (`state_dict["nsides"]`) and stores
    the relevant numeric result of the scan. Ideally it should serve as
    the basic data structure for plotting / processing / transmission of
    the scan result.

    The `state_dict` as produced by `load_cache_state()` is currently structured as follows:
    - 'GCDQp_packet'
    - 'baseline_GCD_file'
    - 'nsides'

    nsides_dict (`state_dict['nsides']`) is a dictionary having per
    indices the 'nside' values for which a scan result is available
    (e.g. 8, 64, 512). The scan result is a dictionary:
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

    require_equal = ["index"]
    require_close = {"llh": 1e-5, "E_in": 1e-4, "E_tot": 1e-2}
    isclose_ignore_zeros = ["E_in", "E_tot"]
    pixel_type = np.dtype(
        [("index", int), ("llh", float), ("E_in", float), ("E_tot", float)]
    )

    def __init__(self, result):
        self.logger = logging.getLogger(__name__)
        self.result = result

    """
    Comparison operators and methods
    """

    def __eq__(self, other):
        # NOTE: will return false if NaN are present
        # numpy.array_equal() supports `equal_nan` option only from version 1.19
        return all(
            np.array_equal(self.result[nside], other.result[nside])
            for nside in (self.result.keys() & other.result.keys())  # think different
        )

    @classmethod
    def get_diff_and_test_vals(
        cls, s_val: float, o_val: float, field: str, equal_nan: bool
    ) -> Tuple[float, bool]:
        """Get the diff float-value and test truth-value for the 2 pixel datapoints."""
        if field in cls.require_equal:
            return s_val - o_val, s_val == o_val
        if field in cls.isclose_ignore_zeros and (s_val == 0.0 or o_val == 0.0):
            return float("nan"), True
        try:
            rdiff = (abs(s_val - o_val) - ATOL) / abs(o_val)  # used by np.isclose
        except ZeroDivisionError:
            rdiff = float("inf")
        return (
            rdiff,
            bool(
                np.isclose(
                    s_val,
                    o_val,
                    equal_nan=equal_nan,
                    rtol=cls.require_close[field],
                    atol=ATOL,
                )
            ),
        )

    def is_close(
        self,
        other: "ScanResult",
        equal_nan: bool = True,
        dump_json_diff: Optional[Path] = None,
    ) -> bool:
        """
        Checks if two results are close by requiring strict equality on pixel indices and close condition on numeric results.

        Optionally, pass a `Path` for `dump_json_diff` to get a json
        file containing every diff at the pixel-data level.
        """
        close: Dict[str, bool] = {}  # one bool for each nside value
        diffs = []  # a large (~4x size of self.results) list of dicts w/ per-pixel info

        # now check individual nside-iterations
        for nside in sorted(self.result.keys() & other.result.keys(), reverse=True):
            self.logger.debug(f"Comparing for nside={nside}")

            # Q: why aren't we using np.array_equal and np.allclose?
            # A: we want detailed pixel-level diffs w/out repeating detailed code

            # zip-iterate each pixel-data
            nside_diffs = []
            for sre_pix, ore_pix in it.zip_longest(
                self.result.get(nside, []),  # empty-list -> fillvalue
                other.result.get(nside, []),  # empty-list -> fillvalue
                fillvalue=np.full((len(self.pixel_type.names),), np.nan),  # 1 vector
            ):
                diff_and_test_vals = [
                    self.get_diff_and_test_vals(float(s), float(o), field, equal_nan)
                    for s, o, field in zip(sre_pix, ore_pix, self.pixel_type.names)
                ]
                nside_diffs.append(
                    [
                        tuple(sre_pix.tolist()),
                        tuple(ore_pix.tolist()),
                        tuple(dat[0] for dat in diff_and_test_vals),  # diff float-value
                        tuple(dat[1] for dat in diff_and_test_vals),  # test truth-value
                    ]
                )

            if dump_json_diff:  # can be a lot of data, so only save it if we're dumping
                diffs.append(nside_diffs)

            # aggregate test-truth values
            nside_equal = {
                field: all(
                    d[3][self.pixel_type.names.index(field)] for d in nside_diffs
                )
                for field in self.require_equal
            }
            nside_close = {
                field: all(
                    d[3][self.pixel_type.names.index(field)] for d in nside_diffs
                )
                for field in self.require_close
            }
            close[nside] = all(nside_equal.values()) and all(nside_close.values())

            # log results (test-truth values)
            if not all(nside_equal.values()):
                self.logger.debug(f"Mismatched pixel indices for nside={nside}")
            if not all(nside_close.values()):
                self.logger.debug(f"Mismatched numerical results for nside={nside}")
                self.logger.debug(f"{nside_close}")

        # finish up

        result = all(close.values())
        self.logger.debug(f"Comparison result: {close}")

        if dump_json_diff:
            with open(dump_json_diff, "w") as f:
                self.logger.info(f"Writing diff to {dump_json_diff}...")
                json.dump(diffs, f, indent=3)

        return result

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
    def from_nsides_dict(cls, nsides_dict) -> "ScanResult":
        """
        Factory method for nsides_dict (`state_dict["nsides"]`)
        """
        result = cls.load_pixels(nsides_dict)
        return cls(result)

    @classmethod
    def load_pixels(cls, nsides_dict):
        logger = logging.getLogger(__name__)

        out = dict()

        for nside in nsides_dict:

            n = len(nsides_dict[nside])
            v = np.zeros(n, dtype=cls.pixel_type)

            logger.info(f"nside {nside} has {n} pixels / {12 * nside**2} total.")

            for i, pixel in enumerate(sorted(nsides_dict[nside])):
                pixel_data = nsides_dict[nside][pixel]
                try:
                    llh = pixel_data["llh"]
                    E_in = pixel_data["recoLossesInside"]
                    E_tot = pixel_data["recoLossesTotal"]
                except KeyError:
                    logger.warning(KeyError)
                    logger.warning(
                        f"Missing data for pixel {pixel} having keys {pixel_data.keys()}"
                    )
                    raise
                v[i] = (pixel, llh, E_in, E_tot)
            key = cls.format_nside(nside)
            out[key] = v

        return out

    """ 
    numpy input / output
    """

    def get_nside_string(self):
        """
        Returns a string string listing the nside values to be included in the output filename.
        """
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
        return cls(result=result)

    def save(self, event_id, output_path=None):
        filename = event_id + "_" + self.get_nside_string() + ".npz"
        if output_path is not None:
            filename = output_path / Path(filename)
        np.savez(filename, **self.result)
        return filename
