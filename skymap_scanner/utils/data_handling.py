from .. import config as cfg  # type: ignore[import]
import os
from pathlib import Path
from typing import Dict, List

from . import LOGGER


class DataStager:
    """
    Class to manage the staging of (spline) data from different sources (in-container, mountpoint, CVMFS, http).
    Some similarity in the paths is assumed.
    """

    def __init__(self, local_paths: List[Path], local_subdir: str, remote_path: str):
        self.local_paths = local_paths
        self.local_subdir = local_subdir
        self.remote_path = remote_path
        self.staging_path = cfg.LOCAL_DATA_CACHE
        self.staging_path.mkdir(exist_ok=True)
        self.map: Dict[str, str] = dict()

    def stage_files(self, file_list: List[str]):
        for basename in file_list:
            for source in self.local_paths:
                subdir = source / self.local_subdir
                filename = subdir / basename
                LOGGER.debug(f"Trying f{filename}.")
                if filename.is_file():
                    LOGGER.debug(f"SUCCESS.")
                    self.map[basename] = str(filename)
                    break
                if self.map.get(basename) is None:
                    LOGGER.debug(f"Staging from HTTP source.")
                    self.map[basename] = self.stage_file(basename)

    def stage_file(self, basename) -> str:
        filesystem_destination_path = self.staging_path / basename

        if filesystem_destination_path.is_file():
            return filesystem_destination_path

        http_source_path = f"{self.remote_path}/{basename}"
        # not sure why we use the -O pattern here
        cmd = f"wget -nv -t 5 -O {filesystem_destination_path} {http_source_path}"
        return_value = os.system(cmd)
        if return_value != 0:
            raise RuntimeError(f"Failed to retrieve data from remote source:\n-> {cmd}")
        else:
            return filesystem_destination_path

    def get_filepath(self, basename):
        return self.map.get(basename)
