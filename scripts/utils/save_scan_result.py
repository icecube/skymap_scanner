"""Create a .npz file from the cache dir (by loading a state_dict).

This is only helpful for generating historical scans, as v3 scans
already have a .npz file created.
"""

import argparse
import logging

from icecube import dataio
from skymap_scanner import load_cache_state
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

    """
    The output filename is partially built inside the ScanResult class.
    """
    result = ScanResult.from_nsides_dict(state_dict["nsides"])
    output_file = result.save(eventID, output_path=args.output_path)

    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
