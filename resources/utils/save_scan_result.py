"""Create a .npz file from the cache dir (by loading a state_dict).

This is only helpful for generating historical scans, as v3 scans
already have a .npz file created.
"""

import argparse
import logging

import skymap_scanner.config as cfg
from skymap_scanner.utils.load_scan_state import load_cache_state
from skymap_scanner.utils.scan_result import ScanResult


def main():
    """Loads the scan result for a given event ID from a cache directory and
    writes the numerical results on a numpy file."""

    logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Scan cache and dumps results to json")

    parser.add_argument("-c", "--cache", help="Cache directory", required=True)
    parser.add_argument("-e", "--event", help="Event ID", required=True)
    parser.add_argument("-o", "--output_path", help="Output path", required=False)
    parser.add_argument(
        "--reco-algo",
        choices=[en.name.lower() for en in cfg.RecoAlgo],
        help="The reconstruction algorithm to use",
    )
    args = parser.parse_args()

    state_dict = load_cache_state(
        args.event,
        cfg.RecoAlgo[args.reco_algo.upper()],
        cache_dir=args.cache,
    )

    """
    The output filename is partially built inside the ScanResult class.
    """
    result = ScanResult.from_nsides_dict(state_dict[cfg.STATEDICT_NSIDES])
    output_file = result.to_npz(eventID, output_path=args.output_path)

    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
