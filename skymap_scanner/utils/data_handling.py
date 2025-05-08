"""Tool for staging data files via local lookup or HTTP download."""

import itertools
import logging
import time
from pathlib import Path
from typing import List

import requests

from .. import config as cfg

LOGGER = logging.getLogger(__name__)


def is_filename(fname: str) -> bool:
    """Return True if fname is a valid filename (no path components)."""
    return fname == str(Path(fname).name)


class DataStager:
    """
    Class to manage the staging of data files from different sources (in-container, mountpoint, CVMFS, http).

    Files are referred to by filename, this way, the user doesn't need to know exactly where a file exists.
    """

    def __init__(self, local_dirs: List[Path], local_subdir: str, remote_url_path: str):
        self.local_dirs = local_dirs
        self.local_subdir = local_subdir

        self.remote_url_path = remote_url_path

        self.staging_path: Path = cfg.LOCAL_DATA_CACHE
        self.staging_path.mkdir(exist_ok=True)

    def stage_files(self, file_list: List[str]):
        """Checks local availability for filenames in a list, and retrieves the missing ones from the HTTP source.

        Args:
            file_list (List[str]): list of file filenames to look up / retrieve.
        """
        LOGGER.info(f"Staging files in filelist: {file_list}")

        # validate
        for fname in file_list:
            if not is_filename(fname):
                raise RuntimeError(
                    f"Cannot stage '{fname}' -- expected a filename without any path components."
                )

        # stage
        for basename in file_list:

            # first: try getting file from a local dir
            try:
                filepath: str = self._get_local_filepath(basename)
                LOGGER.info(f"File {basename} is available at {filepath}.")
                continue
            except FileNotFoundError:
                LOGGER.debug(f"File {basename} is not available on local paths.")

            # backup plan: check staging dir
            try:
                return str(self._get_staging_filepath(basename))
            except FileNotFoundError:
                pass

            # FALL-THROUGH
            # -> download it
            LOGGER.debug("Staging from HTTP source.")
            self._download_file(
                url=f"{self.remote_url_path}/{basename}",
                dest=self.staging_path / basename,
            )

    @staticmethod
    def _download_file(url: str, dest: Path):
        """Retrieves a file from the HTTP source and writes it to the destination.

        Raises:
            RuntimeError: if the file retrieval fails.
        """

        def backoff_sleep(_attempt: int):
            """Sleep with exponential backoff."""
            sleep_duration = 2**_attempt  # Exponential backoff: 2, 4, 8 seconds...
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
                    timeout=(
                        cfg.REMOTE_DATA_DOWNLOAD_TIMEOUT,  # connection timeout
                        cfg.REMOTE_DATA_READ_TIMEOUT,  # read timeout - useful for huge files
                    ),
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
            # NOTE: this uses the 'REMOTE_DATA_READ_TIMEOUT' timeout value, set above
            with open(dest, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        except IOError as e:
            raise RuntimeError(f"File download failed during file write: {e}") from e

        # Step 3: Ensure the file was created successfully
        if dest.is_file():
            LOGGER.info(f"File successfully created at {dest}.")
        else:
            raise RuntimeError(
                f"File download failed during file write (file is invalid):\n-> {dest}."
            )

    def get_filepath(self, filename: str) -> str:
        """Look up basename under the local paths and the staging path and returns the first valid filename.

        Args:
            filename (str): file basename to look up.

        Returns:
            str: valid filename.
        """
        # validate
        if not is_filename(filename):
            raise RuntimeError(
                f"Cannot retrieve '{filename}' -- expected a filename without any path components.'"
            )

        # get file from a local dir
        try:
            return self._get_local_filepath(filename)
        except FileNotFoundError:
            pass

        # backup plan: look at staging dir
        try:
            return str(self._get_staging_filepath(filename))
        except FileNotFoundError:
            pass

        # FALL-THROUGH
        raise FileNotFoundError(
            f"File {filename} is not available in any local or staging path."
        )

    def _get_staging_filepath(self, filename: str) -> Path:
        """Look up filename on staging dir path."""
        filepath = self.staging_path / filename

        if not filepath.is_file():
            FileNotFoundError(f"File {filename} is not in staging dir ({filepath}).")

        LOGGER.info(f"File {filename} available at {filepath}.")
        return filepath

    def _get_local_filepath(self, filename: str) -> str:
        """Look up filename on local paths and return the first matching filename.

        Args:
            filename (str): the filename of the file to look up.

        Returns:
            str: the file path of the file if available
        """
        LOGGER.debug(f"Look up file {filename}.")

        for source in self.local_dirs:
            filepath = source / self.local_subdir / filename
            LOGGER.debug(f"Trying to read {filepath}...")
            if filepath.is_file():
                LOGGER.debug("-> file found")
                return str(filepath)
            else:
                LOGGER.debug("-> file not found")

        # FALL-THROUGH
        # -> File was not found in local paths.
        raise FileNotFoundError(f"File {filename} is not available on any local path.")


def get_gcd_datastager() -> DataStager:
    """Get a DataStager instance configured for GCD files."""
    return DataStager(
        local_dirs=cfg.LOCAL_GCD_DATA_SOURCES,
        local_subdir=cfg.LOCAL_GCD_SUBDIR,
        remote_url_path=cfg.REMOTE_GCD_DATA_SOURCE,
    )
