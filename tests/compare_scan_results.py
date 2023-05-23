"""Testing script for comparing two scan results (.npz files)."""

import argparse
import logging
import sys
from pathlib import Path

from skyreader import SkyScanResult
from wipac_dev_tools import logging_tools


def read_file(filepath: Path) -> SkyScanResult:
    if filepath.suffix == ".json":
        return SkyScanResult.read_json(filepath)
    elif filepath.suffix == ".npz":
        return SkyScanResult.read_npz(filepath)
    else:
        raise Exception("Unsupported file type: {filepath}")


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
    parser.add_argument(  # TODO: remove?
        "--disqualify-zero-energy-pixels",
        default=False,
        action="store_true",
        help='whether a zero-energy pixel value "disqualifies" the entire pixel\'s numerical results',
    )

    args = parser.parse_args()
    logging_tools.log_argparse_args(args, logger=logger, level="WARNING")

    if not read_file(args.actual).has_metadata():
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
        args.disqualify_zero_energy_pixels,  # TODO: remove?
    )


def compare_then_exit(
    actual: SkyScanResult,
    actual_fpath: Path,
    expected: SkyScanResult,
    expected_fpath: Path,
    do_assert: bool,
    diff_out_dir: str,
    logger: logging.Logger,
    do_disqualify_zero_energy_pixels: bool,  # TODO: remove?
) -> None:
    """Compare the results, dump a json diff file, and sys.exit."""
    dump_json_diff = (
        Path(diff_out_dir) / f"{actual_fpath.name}-{expected_fpath.name}.diff.json"
    )

    # increase tolerances
    actual.require_close["E_in"] = 0.07
    actual.require_close["E_tot"] = 0.07

    close = actual.is_close(
        expected,
        dump_json_diff=dump_json_diff,
        do_disqualify_zero_energy_pixels=do_disqualify_zero_energy_pixels,  # TODO: remove?
    )
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
