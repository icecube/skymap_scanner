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

    logger.info(f"Allocated filestagers: {stagers}")

    gcd_manager = GCDManager(config.gcd_dir, filestager=stagers)

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
    realtime_event = RealtimeEvent(event_dict, extract=True)

    run, evt = realtime_event.get_run(), realtime_event.get_event_number()

    icecube_event = realtime_event.get_event()

    logger.info(f"Read {args.event} corresponding to {realtime_event.get_uid()}")

    """
    Access and dump physics frame.
    """
    phys = icecube_event.get_physics_frame()

    logger.debug(phys)

    """
    Allocate path.
    """
    path = cache.allocate_dir(realtime_event.get_stem())

    logger.info(f"Allocated event cache in {path}")

    """
    Check Frame packet
    """
    frame_packet = icecube_event.get_frame_packet()

    logger.info(frame_packet)

    """
    Check GCD
    """
    if frame_packet.has_gcd():
        pass
    else:
        gcd_path = gcd_manager.get_gcd_path(run)
        gcd_packet = gcd_manager.load_gcd(gcd_path)
        frame_packet.set_gcd(gcd_packet)

        logger.info(f"Frame packet has empty GCD. Using {gcd_path}")

    logging.info(icecube_event.frame_packet.frames[0])

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
