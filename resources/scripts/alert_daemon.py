import os
import logging
import argparse
import pickle

from icecube import realtime_tools

from slack_tools import SlackInterface
from slack_tools import MessageHelper as msg

from daemon_conf import shifters_slackid


def get_cache_path():
    # logic copied from realtime_tools/python/config.py
    path = os.path.expandvars('/scratch/$USER')
    if not os.path.isdir(SCRATCH):
        # use system temp directory when scratch is not available
        path = tempfile.gettempdir()
    return path


def make_cache_dir(cache_name='skymap_scanner_cache'):
    cache_dir = os.path.join(
        get_cache_path(), cache_name)
    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)
        # maybe shlould go in a try / except OSError block
    return cache_dir


def handle_event(varname, topics, event):

    uid = 'evt_' + event["time"]  # no need to hash here (?)

    event_cache_dir = make_cache_dir()  # not optimal

    event_filename = uid + '.pkl'
    event_filepath = os.path.join(event_cache_dir, event_filename)

    with open(event_filepath, "wb") as event_file:
        pickle.dump(event, event_file)

    print("Saved event to {}".format(event_filepath))

    print("Event keys are: {}".format(event.keys()))

    # ideally here we span a subprocess


if __name__ == '__main__':

    # ========
    # LOGGING
    # ========

    log = logging.getLogger(__name__)

    log.setLevel(logging.INFO)

    # ================
    # ARGUMENT PARSER
    # ================

    parser = argparse.ArgumentParser(description='Alert Listener v3')

    parser.add_argument("-x", "--execute",
                        action="store_true", dest="execute", default=False,
                        help="Send scans to cluster")
    parser.add_argument("-l", "--localhost",
                        action="store_true", dest="localhost", default=False,
                        help="Listen to localhost for alerts")
    parser.add_argument("-s", "--slackchannel",
                        dest="slackchannel", default="#test_messaging",
                        help="Slack channel")
    parser.add_argument("-n", "--nworkers",
                        dest="nworkers", default=1000,
                        help="Number of workers to send out")

    args = parser.parse_args()

    # ================
    # SLACK INTERFACE
    # ================

    slack = SlackInterface(whoami="New Alert Daemon")

    slack.set_channel(args.slackchannel)

    # ================
    # MAIN LOGIC
    # ================

    if args.localhost:
        log.info("Listening to localhost for alerts")
        # overwriting config variables on an external module is not the best design, but that is how `make_receiver` works
        # see issue https://github.com/icecube/realtime/issues/6
        realtime_tools.config.ZMQ_HOST = 'localhost'
        realtime_tools.config.ZMQ_SUB_PORT = 5556

    slack.post(msg.switch_on(realtime_tools.config.ZMQ_HOST, args.execute))

    # tentatively hardcoded but could better fit in the config file
    stream = 'realtimeEventData'
    topics = ['HESE', 'EHE', 'ESTRES', 'realtimeEventData', 'neutrino']

    try:
        realtime_tools.make_receiver(
            varname=stream, topic=topics, callback=handle_event)
    except Exception as err:
        exception_message = f'Type: {type(err)}\n Message: {err}\n Traceback:\n{err.__traceback__}'
        slack.post(msg.switch_off(shifters_slackid, exception_message))
        raise err
