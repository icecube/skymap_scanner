"""Testing script for comparing two scan results (.npz files)."""

import argparse
import logging
import os
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
        "-f", "--files", help="Files to compare", nargs=2, required=True
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

    results = [ScanResult.load(Path(f)) for f in args.files]
    alpha, beta = results[0], results[1]

    # compare
    close = alpha.is_close(beta)
    equal = alpha == beta

    logger.info(f"The loaded files are close? ({close}) and/or equal? ({equal}).")

    if equal or close:
        sys.exit(0)
    else:
        alpha.dump_json_diff(
            beta,
            Path(args.diff_out_dir)
            / f"{os.path.basename(args.files[0])}-{os.path.basename(args.files[1])}.diff.json",
        )
        if args.do_assert:
            assert False
        sys.exit(1)


if __name__ == "__main__":
    main()
