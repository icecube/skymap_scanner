import logging
import numpy as np


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
        return all(
            np.array_equal(self.result[nside], other.result[nside])
            for nside in self.result
        )

    def is_close(self, other):
        """
        Checks if two results are close by requiring strict equality on pixel indices and close condition on numeric results.
        """
        sre, ore = self.result, other.result  # just for brevity

        require_equal = ["index"]
        require_close = ["llh", "E_in", "E_tot"]

        close = list()  # one bool for each nside value

        for nside in sre:
            nside_equal = [
                np.array_equal(sre[nside][key], ore[nside][key])
                for key in require_equal
            ]
            nside_close = [
                np.allclose(sre[nside][key], ore[nside][key]) for key in require_close
            ]
            close.append(all(nside_equal) and all(nside_close))

        return all(close)

    """
    Auxiliary methods
    """

    @staticmethod
    def format_nside(nside):
        return f"nside-{nside}"

    @staticmethod
    def parse_nside(key):
        return int(key.split("nside-")[1])

    """
    Factory method for state_dict
    """

    @classmethod
    def from_state_dict(cls, state_dict):
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
                llh = pixel_data["llh"]
                E_in = pixel_data["recoLossesInside"]
                E_tot = pixel_data["recoLossesTotal"]
                v[i] = (pixel, llh, E_in, E_tot)
            key = cls.format_nside(nside)
            out[key] = v

        return out

    """ 
    numpy input / output
    """

    @classmethod
    def load(cls, filename):
        npz = np.load(filename)
        result = dict()
        for key in npz.keys():
            result[key] = npz[key]
        return cls(result=result)

    def save(self, filename):
        np.savez(filename, **self.result)


from icecube.skymap_scanner import load_cache_state
from icecube import dataio

import argparse


def main():
    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument("-c", "--cache", help="Cache directory", required=True)
    parser.add_argument("-e", "--event", help="Event ID", required=True)
    parser.add_argument("-o", "--output_file", help="Output file", required=False)

    args = parser.parse_args()

    stagers = dataio.get_stagers()
    eventID, state_dict = load_cache_state(
        args.event, filestager=stagers, cache_dir=args.cache
    )

    if args.output_file is None:
        output_file = eventID + ".npz"
    else:
        output_file = args.output_file

    result = ScanResult.from_state_dict(state_dict)
    result.save(output_file)

    result_check = ScanResult.load(output_file)

    close = result.is_close(result_check)
    equal = result == result_check

    logger.info(
        f"The loaded file is close? ({close}) and equal? ({equal}) to the source data."
    )


if __name__ == "__main__":
    main()
