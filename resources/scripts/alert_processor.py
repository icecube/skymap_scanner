import pickle
import argparse
import logging
from pathlib import Path

from daemon_lib import RealtimeEvent

if __name__ == '__main__':
    log = logging.getLogger(__name__)

    log.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description='Millipede Scanner')
    parser.add_argument('-e', '--event', help='Event file to process')
    args = parser.parse_args()

    event_filepath = Path(args.event)

    with open(event_filepath, 'rb') as event_file:
        event_dict = pickle.load(event_file)

    event_object = RealtimeEvent(event_dict)

    log.info(
        f'Read {args.event} corresponding to f{event_object.get_unique_id()}')

    log.info('Nothing to be done (at the moment), cleaning up the event file')

    event_filepath.unlink()
