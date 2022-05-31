import logging
import os
import tempfile
import subprocess
import pickle


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
            to be verified if this new approach is robust 
        '''
        unique_id = event['value']['data']['unique_id']

        # dashes are preferred to dots in directory names
        uid = unique_id.replace('.', '-')
        return uid

    def handle_event(self, varname, topics, event):
        uid = self.get_uid(event)
        cache_dir = self.cache.dir
        event_filepath = os.path.join(cache_dir, uid + '.pkl')
        log_filepath = os.path.join(cache_dir, uid + '.log')
        with open(event_filepath, 'wb') as event_file:
            pickle.dump(event, event_file)
        self.log.info("Incoming event written to {}".format(event_filepath))

        alert_processor = os.path.dirname(
            os.path.abspath(__file__)) + "/alert_processor.py"

        with open(log_filepath, 'w') as logfile:
            subprocess.run(['python', alert_processor, '-e',
                           event_filepath], stdout=logfile, stderr=logfile)


class RealtimeEvent():
    def __init__(self, event) -> None:
        self.event = event
        pass

    def get_message_time(self):
        return self.event['time']

    def get_unique_id(self):
        return self.event['value']['data']['unique_id']
