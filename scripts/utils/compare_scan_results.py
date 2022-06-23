import argparse
import logging

from pathlib import Path

from numpy import append


from skymap_scanner.scan_result import ScanResult


def main():
    """
    Loads two scan results in numpy format and return the outcome of the comparison.
    """

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument(
        "-f", "--files", help="Files to compare", nargs=2, required=True
    )

    args = parser.parse_args()

    results = [ScanResult.load(Path(f)) for f in args.files]

    close = results[0].is_close(results[1])
    equal = results[0] == results[1]

    logger.info(
        f"The loaded file is close? ({close}) and/or equal? ({equal}) to the source data."
    )

    if equal or close:
        return 0
    else:
        return 1


if __name__ == "__main__":
    main()
