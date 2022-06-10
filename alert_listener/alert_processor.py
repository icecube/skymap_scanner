import pickle
import argparse
import logging
from pathlib import Path
from slack_tools import SlackInterface

from daemon_lib import RealtimeEvent

from icecube import dataio

if __name__ == '__main__':
    log = logging.getLogger(__name__)

    log.setLevel(logging.INFO)

    slack = SlackInterface()

    parser = argparse.ArgumentParser(description='Millipede Scanner')
    parser.add_argument('-e', '--event', help='Event file to process')
    args = parser.parse_args()

    """
    Load event.
    """

    event_filepath = Path(args.event)

    with open(event_filepath, 'rb') as event_file:
        event_dict = pickle.load(event_file)

    event = RealtimeEvent(event_dict)

    log.info(
        f'Read {args.event} corresponding to f{event_object.get_unique_id()}')

    run = event.get_run()
    evt = event.get_event_number()

    """
    Allocate filestagers.
    """

    stagers = dataio.get_stagers()

    """
    Preprocessing the event.
    """

    '''
    Code from original listener to be converted.
        event_id, state_dict = extract_json_message(
            event, filestager=stagers,
            cache_dir=event_cache_dir,
            override_GCD_filename=gcd_dir
        )
        [run, evt, _] = event_id.split(".")
    '''
    # event_id can be already retrieved from the event dictionary
    frame_packet =

    """
    Cleanup.
    """

    log.info('Cleaning up the event file')

    event_filepath.unlink()
