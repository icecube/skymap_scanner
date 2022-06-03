import logging
import os
import tempfile
import subprocess
import pickle

'''
Could be useful to have a logger that can optionally post to slack?

from logging import Logger

class FlexiLogger(Logger):
    # not sure this works because of how super() is resolved
    log_func = { 'info':super().info, 'debug':super().debug, 'warning':super().warning, 'error':super().error }

    def __init__(self, SlackInterface):
        self.slack = SlackInterface
        self.log = logging.getLogger(__name__)

    def log(level='info', slack=False, message=None):
        if slack:
            self.slack.post(message)
        self.log_func[level](message)
'''


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
        self.log = logging.getLogger(__name__)

    def __call__(self, varname, topics, event):
        self.handle_event(varname, topics, event)

    def handle_event(self, varname, topics, event):
        evt = RealtimeEvent(event)

        cache_dir = self.cache.dir

        try:
            stem = evt.get_stem()
        except KeyError as err:
            self.log.error(
                f'Pending event payload is missing or incomplete. Error: {err}')
            return

        # TODO: replace with pathlib Path for readability?
        event_filepath = os.path.join(cache_dir, stem + '.pkl')
        log_filepath = os.path.join(cache_dir, stem + '.log')

        self.log.info(f"Writing incoming event to {event_filepath}")
        with open(event_filepath, 'wb') as event_file:
            pickle.dump(event, event_file)

        alert_processor = os.path.dirname(
            os.path.abspath(__file__)) + "/alert_processor.py"

        self.log.info(
            f"Processing event with subprocess, check {log_filepath}")
        with open(log_filepath, 'w') as logfile:
            subprocess.run(['python', alert_processor, '-e',
                           event_filepath], stdout=logfile, stderr=subprocess.STDOUT)


class RealtimeEvent():
    def __init__(self, event) -> None:
        self.event = event
        pass

    def get_message_time(self):
        return self.event['time']

    def get_uid(self):
        return self.event['value']['data']['unique_id']

    def get_run(self):
        return self.event['value']['data']['run_id']

    def get_event_number(self):
        return self.event['value']['data']['event_id']

    def get_stem(self):
        '''
            filename stem based on evt and run number
            in origin this was based on a hash of event['time']
            to be verified if this new approach is equally robust 
        '''
        uid = self.get_uid()
        # dashes are preferred to dots in directory names
        stem = uid.replace('.', '-')

        return stem

    def get_alert_streams():
        # previous code used this for no apparent good reason:
        # [str(x) for x in event["value"]["streams"]]
        return event['value']['streams']

    '''
    def stem_from_message_time(self):
        # provides uid based on timestamp
        # tentatively superseded
        sep = '-'
        buf = self.event['time']
        buf = buf.replace('-', '')
        buf = buf.replace(' ', sep)
        buf = buf.replace(':', '')
        buf = buf.replace('.', sep)
        return buf
    '''
