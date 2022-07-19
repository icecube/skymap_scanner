"""Testing script for comparing two scan results (.npz files)."""

import argparse
import logging
import sys
from pathlib import Path

from skymap_scanner.server.scan_result import ScanResult


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
        help="The first (actual) npz file",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-e",
        "--expected",
        help="The second (expected) npz file",
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

    compare_then_exit(
        ScanResult.load(args.actual),
        args.actual,
        ScanResult.load(args.expected),
        args.expected,
        args.do_assert,
        args.diff_out_dir,
        logger,
    )


def compare_then_exit(
    actual: ScanResult,
    actual_fpath: Path,
    expected: ScanResult,
    expected_fpath: Path,
    do_assert: bool,
    diff_out_dir: str,
    logger: logging.Logger,
) -> None:
    """Compare the results, dump a json diff file, and sys.exit."""
    dump_json_diff = (
        Path(diff_out_dir) / f"{actual_fpath.name}-{expected_fpath.name}.diff.json"
    )

    # compare
    close = actual.is_close(expected, dump_json_diff=dump_json_diff)
    equal = actual == expected

    logger.info(f"The loaded files are close? ({close}) and/or equal? ({equal}).")

    if equal or close:
        sys.exit(0)
    else:
        if do_assert:
            assert False
        sys.exit(1)


if __name__ == "__main__":
    main()
