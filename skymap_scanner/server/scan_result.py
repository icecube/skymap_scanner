"""For encapsulating the results of an event scan in a single instance."""

import itertools as it
import json
import logging
from pathlib import Path

import numpy as np


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

    def is_close(self, other, equal_nan=True) -> bool:
        """
        Checks if two results are close by requiring strict equality on pixel indices and close condition on numeric results.
        """
        close = dict()  # one bool for each nside value

        # first check which nsides were used
        if sorted(self.result.keys()) != sorted(other.result.keys()):
            self.logger.warning(
                f"Mismatched nsides: {sorted(self.result.keys())} vs {sorted(other.result.keys())}"
            )
            close["same-nsides"] = False

        # now check individual nside-iterations
        for nside in sorted(self.result, reverse=True):
            self.logger.debug(f"Comparing for nside={nside}")
            sre, ore = self.result[nside], other.result[nside]  # brevity

            if len(sre) != len(ore):
                self.logger.warning(
                    f"Mismatched ndarray lengths: {len(sre)} vs {len(ore)}"
                )
                close[nside] = False
                continue  # we can't go on

            nside_equal = {
                key: np.array_equal(sre[key], ore[key]) for key in self.require_equal
            }
            nside_close = {
                # np.allclose() expects equal shapes so we need to check for that first
                key: (
                    sre[key].shape == ore[key].shape
                    and np.allclose(
                        sre[key],
                        ore[key],
                        equal_nan=equal_nan,
                        rtol=rtol,
                    )
                )
                for key, rtol in self.require_close.items()
            }
            close[nside] = all(nside_equal.values()) and all(nside_close.values())

            # log results
            if not all(nside_equal.values()):
                self.logger.debug(f"Mismatched pixel indices for nside={nside}")
            if not all(nside_close.values()):
                self.logger.debug(f"Mismatched numerical results for nside={nside}")
                self.logger.debug(f"{nside_close}")

        result = all(close.values())

        if not result:
            self.logger.debug(f"Comparison result: {close}")

        return result

    def dump_json_diff(self, expected, json_fpath) -> dict:
        """Get a python-native dict of the diff of the two results."""
        diffs = dict()

        def diff_element(act, exp):
            if act is None or exp is None:
                return None
            return abs((act - exp) / exp)  # relative error

        for nside in self.result.keys() & expected.result.keys():  # think different
            joined = []
            for actual_pix, expect_pix in it.zip_longest(
                self.result.get(nside, []),
                expected.result.get(nside, []),
                fillvalue=(None,) * len(self.result[nside][0]),
            ):
                if not isinstance(actual_pix, tuple):
                    actual_pix = tuple(actual_pix.tolist())
                if not isinstance(expect_pix, tuple):
                    expect_pix = tuple(expect_pix.tolist())
                joined.append(
                    (
                        actual_pix,
                        expect_pix,
                        tuple(
                            map(
                                lambda i, j: diff_element(i, j),
                                actual_pix,
                                expect_pix,
                            )
                        ),
                    )
                )
            diffs[nside] = joined

        with open(json_fpath, "w") as f:
            self.logger.info(f"Writing diff to {json_fpath}...")
            json.dump(diffs, f, indent=3)
        return diffs

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
