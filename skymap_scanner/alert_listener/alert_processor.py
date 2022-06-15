import pickle
import argparse
import logging
import sys

from pathlib import Path

from cache_manager import CacheManager
import config
from realtime_event import RealtimeEvent
from slack_tools import SlackInterface

from icecube import dataio

from skymap_scanner.extract_json_message import extract_json_message
from gcd import GCDManager


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

    gcd = GCDManager(config.gcd_dir)

    """
    Load event.
    """

    event_filepath = Path(args.event)

    with event_filepath.open(mode="rb") as event_file:
        event_dict = pickle.load(event_file)

    """
    Allocate filestagers.
    """
    stagers = dataio.get_stagers()

    """
    Test old code
    """
    """
    event_old = extract_json_message(
        event_dict,
        filestager=stagers,
        cache_dir=cache.dir,
        override_GCD_filename=config.gcd_dir,
    )
    """

    """
    Test new code
    """
    event = RealtimeEvent(event_dict, extract_frames=True)

    logger.info(f"Read {args.event} corresponding to {event.get_uid()}")

    run, evt = event.get_run(), event.get_event_number()

    """
    Access and dump physics frame.
    """
    phys = event.get_physics_frame()

    logger.debug(phys)

    """
    Allocate path.
    """
    path = cache.allocate_dir(event.get_stem())

    logger.info(f"Allocated event cache in {path}")

    """
    Check Frame packet
    """
    frame_packet = event.get_frame_packet()

    logger.info(frame_packet)

    """
    Check GCD
    """
    if not event.frame_packet.has_gcd():
        gcd_path = gcd.get_gcd_path(run)
        logger.info(f"Frame packet has empty GCD. Using {gcd_path}")
        event.frame_packet.set_gcd(gcd_path)
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
