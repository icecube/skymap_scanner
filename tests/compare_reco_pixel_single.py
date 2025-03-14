"""Testing script for comparing two reco pixel outfiles."""

import argparse
import json
import logging
from pathlib import Path

from skyreader import SkyScanResult, EventMetadata
from wipac_dev_tools import logging_tools

from compare_scan_results import compare_then_exit
from skymap_scanner.config import MSG_KEY_RECO_PIXEL_VARIATION_PKL_B64
from skymap_scanner.utils import to_skyscan_result
from skymap_scanner.utils.messages import Serialization
from skymap_scanner.utils.pixel_classes import RecoPixelFinal


def load_from_outfile(outfile_fpath: Path) -> SkyScanResult:
    """Load a SkyScanResult from the outfile."""
    with open(outfile_fpath, "r") as f:
        msg = json.load(f)

    pixfin = RecoPixelFinal.from_recopixelvariation(
        Serialization.decode_pkl_b64(msg[MSG_KEY_RECO_PIXEL_VARIATION_PKL_B64])
    )
    return to_skyscan_result.from_nsides_dict(
        {pixfin.nside: {pixfin.pixel_id: pixfin}},
        is_complete=True,
        event_metadata=EventMetadata(0, 0, "", 0., False)
    )


def main():
    """Loads two scan results in numpy format and exit with the outcome of the
    comparison."""

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument(
        "-a",
        "--actual",
        help="The first (actual) outfile",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-e",
        "--expected",
        help="The second (expected) outfile",
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

    args = parser.parse_args()
    logging_tools.log_argparse_args(args, logger=logger, level="WARNING")

    actual = load_from_outfile(args.actual)
    expected = load_from_outfile(args.expected)

    compare_then_exit(
        actual,
        args.actual,
        expected,
        args.expected,
        args.do_assert,
        args.diff_out_dir,
        logger,
    )


if __name__ == "__main__":
    main()
