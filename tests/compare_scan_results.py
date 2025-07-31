"""Testing script for comparing two scan results (.npz files)."""

import argparse
import logging
import sys
from pathlib import Path

from skyreader import SkyScanResult
from wipac_dev_tools import logging_tools

RTOL_PER_FIELD = {
    "llh": 0.1,
    "E_in": 0.01,
    "E_tot": 0.01,
    "X": 0.1,
    "Y": 0.1,
    "Z": 0.1,
    "T": 0.01,
}


def read_file(filepath: Path) -> SkyScanResult:
    if filepath.suffix == ".json":
        return SkyScanResult.read_json(filepath)
    elif filepath.suffix == ".npz":
        return SkyScanResult.read_npz(filepath)
    else:
        raise Exception(f"Unsupported file type: {filepath}")


def main():
    """Loads two scan results in numpy format and exit with the outcome of the
    comparison."""

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument(
        "-a",
        "--actual",
        help="The first (actual) npz file (npz or json)",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-e",
        "--expected",
        help="The second (expected) file (npz or json)",
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
    parser.add_argument(
        "--compare-different-versions-ok",
        default=False,
        action="store_true",
        help="whether it's allowed to compare result objects of different versions (columns, aka numpy dtypes)",
    )

    args = parser.parse_args()
    logging_tools.log_argparse_args(args, logger=logger, level="WARNING")

    if not read_file(args.actual).has_minimal_metadata():
        if args.do_assert:
            assert False
        sys.exit(1)

    compare_then_exit(
        read_file(args.actual),
        args.actual,
        read_file(args.expected),
        args.expected,
        args.do_assert,
        args.diff_out_dir,
        logger,
        compare_different_versions_ok=args.compare_different_versions_ok,
    )


def compare_then_exit(
    actual: SkyScanResult,
    actual_fpath: Path,
    expected: SkyScanResult,
    expected_fpath: Path,
    do_assert: bool,
    diff_out_dir: str,
    logger: logging.Logger,
    compare_different_versions_ok: bool = False,
) -> None:
    """Compare the results, dump a json diff file, and sys.exit."""
    dump_json_diff = (
        Path(diff_out_dir) / f"{actual_fpath.name}-{expected_fpath.name}.diff.json"
    )

    close = actual.is_close(
        expected, dump_json_diff=dump_json_diff, rtol_per_field=RTOL_PER_FIELD
    )

    try:
        equal = actual == expected
    except TypeError as e:
        logger.warning(f"--expected and --actual results are not the same types: {e}")
        if not compare_different_versions_ok:
            raise e
        equal = False

    logger.info(f"The loaded files are close? ({close}) and/or equal? ({equal}).")
    logger.info(f"{RTOL_PER_FIELD=}")
    logger.info("Actual vs Expected...")

    if equal or close:
        logger.info("PASSED.")
        sys.exit(0)
    else:
        logger.info("FAILED!")
        print(  # print so the github actions console can interpret the error
            f"::error::the scan results did not match the expected values ({close=}, {equal=})"
        )
        if do_assert:
            assert False
        sys.exit(1)


if __name__ == "__main__":
    main()
