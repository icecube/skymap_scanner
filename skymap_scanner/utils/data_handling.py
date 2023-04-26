from .. import config as cfg  # type: ignore[import]
from pathlib import Path
import subprocess
from typing import Dict, List, Union

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
        self.staging_path: Path = cfg.LOCAL_DATA_CACHE
        self.staging_path.mkdir(exist_ok=True)

    def stage_files(self, file_list: List[str]):
        """Checks local availability for filenames in a list, and retrieves the missing ones from the HTTP source.

        Args:
            file_list (List[str]): list of file filenames to look up / retrieve.
        """
        LOGGER.debug(f"Staging files in filelist: {file_list}")
        for basename in file_list:
            try:
                filepath: str = self.get_local_filepath(basename)
            except FileNotFoundError:
                LOGGER.debug(
                    f"File {basename} is not available on default local paths."
                )
                if (self.staging_path / basename).is_file():
                    LOGGER.debug("File is available on staging path.")
                else:
                    LOGGER.debug("Staging from HTTP source.")
                    self.stage_file(basename)

            else:
                LOGGER.debug(f"File {basename} is available at {filepath}.")

    def stage_file(self, basename: str):
        """Retrieves a file from the HTTP source.

        Args:
            basename (str): the basename of the file.

        Raises:
            RuntimeError: if the file retrieval fails.
        """
        local_destination_path = self.staging_path / basename
        http_source_path = f"{self.remote_path}/{basename}"
        # not sure why we use the -O pattern here
        cmd = [
            "wget",
            "-nv",
            "-t",
            "5",
            "-O",
            str(local_destination_path),
            http_source_path,
        ]

        subprocess.run(cmd, check=True)

        if not local_destination_path.is_file():
            raise RuntimeError(
                f"Subprocess `wget` succeeded but the resulting file is invalid:\n-> {cmd}"
            )

    def get_filepath(self, filename: str) -> str:
        """Look up basename under the local paths and the staging path and returns the first valid filename.

        Args:
            basename (str): file basename to look up.

        Returns:
            str: valid filename.
        """
        try:
            local_filepath = self.get_local_filepath(filename)
            return local_filepath
        except FileNotFoundError:
            filepath = self.staging_path / filename
            if filepath.is_file():
                return str(filepath)
            else:
                raise FileNotFoundError(
                    f"File {filename} is not available in any local or staging path."
                )

    def get_local_filepath(self, filename: str) -> str:
        """Look up filename on local paths and return the first matching filename.

        Args:
            filename (str): the filename of the file to look up.

        Returns:
            str: the file path of the file if available
        """
        LOGGER.info(f"Look up file {filename}.")
        for source in self.local_paths:
            subdir = source / self.local_subdir
            filepath = subdir / filename
            LOGGER.debug(f"Trying to read {filepath}...")
            if filepath.is_file():
                LOGGER.debug(f"-> success.")
                filename = str(filepath)
                return filename
            else:
                LOGGER.debug(f"-> fail.")
                # File was not found in local paths.
        raise FileNotFoundError(f"File {filename} is not available on any local path.")
