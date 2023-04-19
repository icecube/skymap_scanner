import config as cfg
import os
from pathlib import Path


class DataStager:
    """
    Class to manage the staging of (spline) data from different sources (in-container, mountpoint, CVMFS, http).
    Some similarity in the paths is assumed.
    """

    def __init__(self, subdir: str, write=True):
        self.subdir = subdir
        self.default_path = Path(os.path.expandvars("$I3_DATA")) / subdir
        self.staging_path = cfg.LOCAL_STAGING_PATH
        self.remote_source = cfg.HTTP_DATA_SOURCE
        self.write = write
        if not self.default_path.is_dir():
            raise RuntimeError(
                f"No default directory found at: \n {self.default_path}."
            )
        

    def get_filename(self, basename):
        default_filepath = self.default_path / basename
        
        if default_filepath.is_file():
            return
        elif :
            
        
    def stage_file(self, basename):
        # not sure why we use the -O pattern here
        cmd = f"wget -nv -t 5 -O {self.default_path}/{basename} {self.remote_source}/{self.subdir}/{basename}"
        os.system(cmd)