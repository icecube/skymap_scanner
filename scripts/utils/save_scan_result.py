import argparse
import logging

from pathlib import Path

from icecube import dataio

# not sure why this still has the icecube prefix
from icecube.skymap_scanner import load_cache_state

from skymap_scanner.server.scan_result import ScanResult


def main():
    """
    Loads the scan result for a given event ID from a cache directory and writes the numerical results on a numpy file.
    """

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument("-c", "--cache", help="Cache directory", required=True)
    parser.add_argument("-e", "--event", help="Event ID", required=True)
    parser.add_argument("-o", "--output_path", help="Output path", required=False)

    args = parser.parse_args()

    stagers = dataio.get_stagers()

    eventID, state_dict = load_cache_state(
        args.event, filestager=stagers, cache_dir=args.cache
    )

    output_file = Path(eventID + ".npz")

    if args.output_path is not None:
        output_file = Path(args.output_path / output_file)

    result = ScanResult.from_state_dict(state_dict)
    result.save(output_file)

    result_check = ScanResult.load(output_file)

    close = result.is_close(result_check)
    equal = result == result_check

    logger.info(
        f"The loaded file is close? ({close}) and/or equal? ({equal}) to the source data."
    )

    return equal or close


if __name__ == "__main__":
    main()
