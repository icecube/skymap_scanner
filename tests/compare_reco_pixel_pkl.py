"""Testing script for comparing two reco pixel outputs (.pkl files)."""

import argparse
import logging
import pickle
from pathlib import Path

from skymap_scanner.utils.scan_result import ScanResult
from wipac_dev_tools import logging_tools

from compare_scan_results import compare_then_exit


def main():
    """Loads two scan results in numpy format and exit with the outcome of the
    comparison."""

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument(
        "-a",
        "--actual",
        help="The first (actual) pkl file",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-e",
        "--expected",
        help="The second (expected) pkl file",
        required=True,
        type=Path,
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
    parser.add_argument(  # TODO: remove?
        "--disqualify-zero-energy-pixels",
        default=False,
        action="store_true",
        help='whether a zero-energy pixel value "disqualifies" the entire pixel\'s numerical results',
    )

    args = parser.parse_args()
    logging_tools.log_argparse_args(args, logger=logger, level="WARNING")

    def load_from_out_pkl(out_pkl_fpath: Path) -> ScanResult:
        """Load a ScanResult from the "out" pkl file."""
        with open(out_pkl_fpath, "rb") as f:
            msg = pickle.load(f)

        return ScanResult.from_nsides_dict(
            {msg["pixfin"].nside: {msg["pixfin"].pixel: msg["pixfin"]}}
        )

    actual = load_from_out_pkl(args.actual)
    expected = load_from_out_pkl(args.expected)

    compare_then_exit(
        actual,
        args.actual,
        expected,
        args.expected,
        args.do_assert,
        args.diff_out_dir,
        logger,
        args.disqualify_zero_energy_pixels,  # TODO: remove?
    )


if __name__ == "__main__":
    main()
