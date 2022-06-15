import os
import tempfile
from pathlib import Path


class CacheManager:
    def __init__(self, name="skymap_scanner_cache"):
        self.loc = self.get_cache_location()
        self.cache_dir = self.make_cache_dir(cache_name=name)
        self.path = Path(self.cache_dir)

    def get_cache_location(self):
        # logic borrowed from realtime_tools/python/config.py
        tmp_path = os.path.expandvars("/scratch/$USER")
        if not os.path.isdir(tmp_path):
            # use system temp directory when scratch is not available
            tmp_path = tempfile.gettempdir()
        return tmp_path

    def make_cache_dir(self, cache_name):
        cache_dir = os.path.join(self.loc, cache_name)
        if not os.path.isdir(cache_dir):
            # TODO: maybe should go in a try / except OSError block
            os.makedirs(cache_dir)
        return cache_dir

    def allocate_dir(self, dir_name):
        dir_path = self.path / Path(dir_name)
        if not dir_path.is_dir():
            dir_path.mkdir()
        return dir_path

    @property
    def dir(self):
        return self.cache_dir
