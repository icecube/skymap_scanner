import logging
import numpy as np
from pathlib import Path


class ScanResult:
    """
    This class parses a `state_dict` and stores the relevant numeric result of the scan. Ideally it should serve as the basic data structure for plotting / processing / transmission of the scan result.

    The `state_dict` as produced by `load_cache_state()` is currently structured as follows:
    - 'GCDQp_packet'
    - 'baseline_GCD_file'
    - 'nsides'

    `state_dict['nsides']` is a dictionary having per indices the 'nside' values for which a scan result is available (e.g. 8, 64, 512). The scan result is a dictionary:
    - i (pixel index, integer) -> 'frame', 'llh', 'recoLossesInside', 'recoLossesTotal'

    The numeric values of interest are 'llh', 'recoLossesInside', 'recoLossesTotal'. The pixel indices in the input dictionary are in general unsorted (python dict are unsorted by design) and are incomplete (since fine-grained scans only cover a portion of the HEALPIX area). The class stores the each result in a numpy structured array sorted by the pixel index, which is stored in a dedicated field.

    TODO: implement FITS output.
    """

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
            for nside in self.result
        )

    def is_close(self, other, equal_nan=True):
        """
        Checks if two results are close by requiring strict equality on pixel indices and close condition on numeric results.
        """

        require_equal = ["index"]
        require_close = ["llh", "E_in", "E_tot"]

        close = dict()  # one bool for each nside value

        for nside in self.result:
            sre, ore = self.result[nside], other.result[nside]  # brevity

            nside_equal = {
                key: np.array_equal(sre[key], ore[key]) for key in require_equal
            }
            nside_close = {
                # np.allclose() expects equal shapes so we need to check for that first
                key: (sre[key].shape == ore[key].shape)
                and np.allclose(sre[key], ore[key], equal_nan=equal_nan)
                for key in require_close
            }
            close[nside] = all(nside_equal.values()) and all(nside_close.values())

            if not all(nside_equal.values()):
                self.logger.debug(f"Mismatched pixel indices for nside={nside}")
            if not all(nside_close.values()):
                self.logger.debug(f"Mismatched numerical results for nside={nside}")
                self.logger.debug(f"{nside_close}")

        result = all(close.values())

        if not result:
            self.logger.debug(f"Comparison result: {close}")

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
    def from_state_dict(cls, state_dict):
        """
        Factory method for state_dict
        """
        result = cls.load_pixels(state_dict)
        return cls(result)

    @classmethod
    def load_pixels(cls, state_dict):
        logger = logging.getLogger(__name__)

        out = dict()
        maps = state_dict["nsides"]

        for nside in maps:

            n = len(maps[nside])
            v = np.zeros(n, dtype=cls.pixel_type)

            logger.info(f"nside {nside} has {n} pixels / {12 * nside**2} total.")

            for i, pixel in enumerate(sorted(maps[nside])):
                pixel_data = maps[nside][pixel]
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
        return "_".join(sorted(self.result))

    @classmethod
    def load(cls, filename):
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
