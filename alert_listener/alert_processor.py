import pickle
import argparse
import logging
import sys

from pathlib import Path

from slack_tools import SlackInterface
from realtime_event import RealtimeEvent

from cache_manager import CacheManager

from icecube import dataio

# from ..python.extract_json_message import extract_GCD_diff_base_filename

def main():
    parser = argparse.ArgumentParser(description="Millipede Scanner")
    parser.add_argument("-e", "--event", help="Event file to process")
    parser.add_argument(
        "--read-only", action="store_true", default=False, help="Read only mode"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger(__name__)

    slack = SlackInterface()

    cache = CacheManager()

    """
    Load event.
    """

    event_filepath = Path(args.event)

    with event_filepath.open(mode="rb") as event_file:
        event_dict = pickle.load(event_file)

    event = RealtimeEvent(event_dict, extract_frames=True)

    logger.info(f"Read {args.event} corresponding to {event.get_uid()}")

    run, evt = event.get_run(), event.get_event_number()

    """
    Allocate filestagers.
    """
    stagers = dataio.get_stagers()

    """
    Access and dump physics frame.
    """
    phys = event.get_physics_frame()

    logger.info(phys)

    """
    Allocate path.
    """
    path = cache.allocate_dir(event.get_stem())

    logger.info(f"Allocated event cache in {path}")

    """
    Check GCD
    """

    frame_packet = event.get_frame_packet()

    GCD_diff_base_filename = extract_GCD_diff_base_filename(frame_packet)

    """
    Cleanup.
    """
    if not args.read_only:
        logger.info("Cleaning up the event file")
        event_filepath.unlink()
    else:
        logger.info("Running in read-only mode, input file is preserved.")


if __name__ == "__main__":
    main()
