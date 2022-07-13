"""Testing script for comparing two reco pixel outputs (.pkl files)."""

import argparse
import logging
import os
import pickle
import sys
from pathlib import Path

from skymap_scanner.client.reco_pixel_pkl import read_from_in_pkl
from skymap_scanner.server.scan_result import ScanResult
from skymap_scanner.server.start_scan import PixelRecoSaver


def main():
    """
    Loads two scan results in numpy format and exit with the outcome of the comparison.
    """

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument(
        "-a",
        "--alpha",
        dest="alpha_in_out",
        help="The first in-out couple of reco-pixel pkl files, ex: 123.456.in.pkl 123.456.out.pkl",
        nargs=2,
        required=True,
    )
    parser.add_argument(
        "-b",
        "--beta",
        dest="beta_in_out",
        help="The second in-out couple of reco-pixel pkl files, ex: 789.321.in.pkl 789.321.out.pkl",
        nargs=2,
        required=True,
    )
    parser.add_argument(
        "--assert",
        dest="do_assert",
        default=False,
        action="store_true",
        help="'assert' the results",
    )

    args = parser.parse_args()

    def load_from_in_out_pkls(in_pkl_fpath: Path, out_pkl_fpath: Path) -> ScanResult:
        """Load a ScanResult from an in-pkl file and its out-pkl file."""
        _, GCDQp_packet, baseline_GCD_file = read_from_in_pkl(str(in_pkl_fpath))
        with open(out_pkl_fpath, "rb") as f:
            frame = pickle.load(f)

        pixel_data = PixelRecoSaver.get_pixel_data(
            baseline_GCD_file, GCDQp_packet, frame
        )
        return ScanResult.from_nsides_dict(
            {0: [pixel_data]}  # 0 b/c this isn't a real nside value
        )

    alpha = load_from_in_out_pkls(
        Path(args.alpha_in_out[0]),
        Path(args.alpha_in_out[1]),
    )
    beta = load_from_in_out_pkls(
        Path(args.beta_in_out[0]),
        Path(args.beta_in_out[1]),
    )

    # compare
    close = alpha.is_close(beta)
    equal = alpha == beta

    logger.info(f"The loaded files are close? ({close}) and/or equal? ({equal}).")

    if equal or close:
        sys.exit(0)
    else:
        alpha.dump_json_diff(
            beta,
            f"{os.path.basename(args.files[0])}-{os.path.basename(args.files[1])}.diff.json",
        )
        if args.do_assert:
            assert False
        sys.exit(1)


if __name__ == "__main__":
    main()
