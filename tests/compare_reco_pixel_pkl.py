"""Testing script for comparing two reco pixel outputs (.pkl files)."""

import argparse
import logging
import pickle
from pathlib import Path

from skymap_scanner.client.reco_pixel_pkl import read_from_in_pkl
from skymap_scanner.server.scan_result import ScanResult
from skymap_scanner.server.start_scan import PixelRecoSaver

from compare_scan_results import compare_then_exit


def main():
    """
    Loads two scan results in numpy format and exit with the outcome of the comparison.
    """

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument(
        "-a",
        "--actual",
        dest="actual_in_out",
        help="The first (actual) in-out couple of reco-pixel pkl files, ex: 123.456.in.pkl 123.456.out.pkl",
        nargs=2,
        required=True,
    )
    parser.add_argument(
        "-e",
        "--expected",
        dest="expected_in_out",
        help="The second (expected) in-out couple of reco-pixel pkl files, ex: 789.321.in.pkl 789.321.out.pkl",
        nargs=2,
        required=True,
    )
    parser.add_argument(
        "-d",
        "--diff-out-dir",
        help="Which dir to save any resulting .diff.json file (only if diff exists)",
        default=".",
    )
    parser.add_argument(
        "--assert",
        dest="do_assert",
        default=False,
        action="store_true",
        help="'assert' the results",
    )
    parser.add_argument(
        "--disqualify-zero-energy-pixels",
        default=False,
        action="store_true",
        help='whether a zero-energy pixel value "disqualifies" the entire pixel\'s numerical results',
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

    actual = load_from_in_out_pkls(
        Path(args.actual_in_out[0]),
        Path(args.actual_in_out[1]),
    )
    expected = load_from_in_out_pkls(
        Path(args.expected_in_out[0]),
        Path(args.expected_in_out[1]),
    )

    compare_then_exit(
        actual,
        Path(args.actual_in_out[1]),
        expected,
        Path(args.expected_in_out[1]),
        args.do_assert,
        args.diff_out_dir,
        logger,
        args.disqualify_zero_energy_pixels,
    )


if __name__ == "__main__":
    main()
