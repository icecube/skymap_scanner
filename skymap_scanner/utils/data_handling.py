"""data_handling.py."""

import itertools
import logging
import time
from pathlib import Path
from typing import List

import requests

from .. import config as cfg

LOGGER = logging.getLogger(__name__)


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
                    self.download_file(basename)

            else:
                LOGGER.debug(f"File {basename} is available at {filepath}.")

    def download_file(self, basename: str):
        """Retrieves a file from the HTTP source.

        Args:
            basename (str): the basename of the file.

        Raises:
            RuntimeError: if the file retrieval fails.
        """
        dest = self.staging_path / basename
        url = f"{self.remote_path}/{basename}"

        def backoff_sleep(attempt: int):
            """Sleep with exponential backoff."""
            sleep_duration = 2**attempt  # Exponential backoff: 2, 4, 8 seconds...
            LOGGER.info(f"Retrying file download in {sleep_duration} seconds...")
            time.sleep(sleep_duration)

        # Step 1: Download the file
        for attempt in itertools.count(1):
            if attempt > 1:
                backoff_sleep(attempt)
            # get
            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=cfg.REMOTE_DATA_DOWNLOAD_TIMEOUT,
                )
                response.raise_for_status()  # Check if the request was successful (2xx)
                break
            except requests.exceptions.RequestException as e:
                if attempt > cfg.REMOTE_DATA_DOWNLOAD_RETRIES:  # 'attempt' is 1-indexed
                    raise RuntimeError(
                        f"Download failed after {cfg.REMOTE_DATA_DOWNLOAD_RETRIES} retries: {e}"
                    ) from e

        # Step 2: Write the file
        try:
            with open(dest, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        except IOError as e:
            raise RuntimeError(f"File download failed during file write: {e}") from e

        # Step 3: Ensure the file was created successfully
        if dest.is_file():
            LOGGER.debug(f"File successfully created at {dest}.")
        else:
            raise RuntimeError(
                f"File download failed during file write (file is invalid):\n-> {dest}."
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
                LOGGER.info(f"File {filename} available at {filepath}.")
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
        LOGGER.debug(f"Look up file {filename}.")
        for source in self.local_paths:
            subdir = source / self.local_subdir
            filepath = subdir / filename
            LOGGER.debug(f"Trying to read {filepath}...")
            if filepath.is_file():
                LOGGER.debug("-> success.")
                filename = str(filepath)
                return filename
            else:
                LOGGER.debug("-> fail.")
                # File was not found in local paths.
        raise FileNotFoundError(f"File {filename} is not available on any local path.")


def get_gcd_datastager() -> DataStager:
    return DataStager(
        local_paths=cfg.LOCAL_GCD_DATA_SOURCES,
        local_subdir=cfg.LOCAL_GCD_SUBDIR,
        remote_path=cfg.REMOTE_GCD_DATA_SOURCE,
    )
