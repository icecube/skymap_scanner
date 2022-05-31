import os
import logging
import argparse
import pickle

from icecube import realtime_tools

from slack_tools import SlackInterface
from slack_tools import MessageHelper as msg

from daemon_conf import shifters_slackid

import tempfile
import subprocess


class CacheManager():
    def __init__(self, name='skymap_scanner_cache'):
        self.path = self.get_cache_path()
        self.cache_dir = self.make_cache_dir(cache_name=name)

    def get_cache_path(self):
        # logic borrowed from realtime_tools/python/config.py
        tmp_path = os.path.expandvars('/scratch/$USER')
        if not os.path.isdir(tmp_path):
            # use system temp directory when scratch is not available
            tmp_path = tempfile.gettempdir()
        return tmp_path

    def make_cache_dir(self, cache_name='skymap_scanner_cache'):
        cache_dir = os.path.join(
            self.path, cache_name)
        if not os.path.isdir(cache_dir):
            # TODO: maybe should go in a try / except OSError block
            os.makedirs(cache_dir)
        return cache_dir

    @property
    def dir(self):
        return self.cache_dir


class EventHandler():
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.log = logging.getLogger(self.__name__)

    def __call__(self, varname, topics, event):
        self.handle_event(varname, topics, event)

    def uid_from_message_time(self, event):
        # provides uid based on timestamp
        # tentatively superseded
        sep = '-'
        buf = event['time']
        buf = buf.replace('-', '')
        buf = buf.replace(' ', sep)
        buf = buf.replace(':', '')
        buf = buf.replace('.', sep)
        return buf

    def get_uid(self, event):
        '''
            uid based on evt / run information
            in origin this was based on event['time']
            to be verified if this approach is robust 
        '''
        unique_id = event['value']['data']['unique_id']

        # dashes are preferred to dots in directory names
        uid = unique_id.replace('.', '-')
        return uid

    def handle_event(self, varname, topics, event):
        uid = self.get_uid(event)
        cache_dir = self.cache.dir
        event_filename = uid + '.pkl'
        event_filepath = os.path.join(cache_dir, event_filename)
        with open(event_filepath, 'wb') as event_file:
            pickle.dump(event, event_file)
        self.log.info("Incoming event written to {}".format(event_filepath))

        subprocess.run(['python', 'alert_processor.py', '-e', event_filepath])


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
                        dest="slackchannel", default=None,
                        help="Slack channel")
    parser.add_argument("-n", "--nworkers",
                        dest="nworkers", default=1000,
                        help="Number of workers to send out")

    args = parser.parse_args()

    # ================
    # SLACK INTERFACE
    # ================

    # TODO: better handling of args.slackchannel = None
    slack = SlackInterface(whoami="New Alert Daemon",
                           channel=args.slackchannel, api_keyfile='slack.key')

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

    cache_manager = CacheManager()

    event_handler = EventHandler(cache_manager=cache_manager)

    try:
        realtime_tools.make_receiver(
            varname=stream, topic=topics, callback=event_handler)
    except Exception as err:
        exception_message = f'Type: {type(err)} - Message: {err} -  Traceback: {err.__traceback__}'
        slack.post(msg.switch_off(shifters_slackid, exception_message))
        raise err
