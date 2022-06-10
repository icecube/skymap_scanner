import os
import tempfile


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
