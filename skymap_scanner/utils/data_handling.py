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


class InvalidFilenameException(Exception):
    """Raised when a filename is invalid."""


class DownloadFailedException(Exception):
    """Raised when a download failed."""


class DataStager:
    """
    Class to manage the staging of data files from different sources (in-container, mountpoint, CVMFS, http).

    Files are referred to by filename, this way, the user doesn't need to know exactly where a file exists.
    """

    def __init__(
        self,
        local_data_sources: List[Path],
        local_subdir: str,
        remote_url_path: str,
    ):
        """
        Initialize a DataStager with local sources, a subdirectory, and a remote URL.

        Args:
            local_data_sources (List[Path]):
                base directories to search locally
            local_subdir (str):
                subdirectory within each base directory to search
            remote_url_path (str):
                a base URL for downloading files if not found locally
                (if used, files are cached locally)
        """
        self.local_dirs = [(dpath / local_subdir) for dpath in local_data_sources]

        self.remote_url_path = remote_url_path

        # use the 'local_subdir' in the cache dir path to partition path
        self.cache_dir: Path = cfg.LOCAL_DATA_CACHE / local_subdir
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    def stage_files(self, file_list: List[str]):
        """Checks local availability for filenames in a list, and retrieves the missing ones from the HTTP source.

        Args:
            file_list (List[str]): list of file filenames to look up / retrieve.
        """
        LOGGER.info(f"Staging files: {file_list=}")

        # validate
        for fname in file_list:
            if not is_filename(fname):
                raise InvalidFilenameException(
                    f"Cannot stage {fname=} -- expected a filename without any path components."
                )

        # stage
        for basename in file_list:

            # first: try getting file from a local dir
            try:
                self._get_local_filepath(basename)
                continue
            except FileNotFoundError:
                pass

            # backup plan: check cache dir
            try:
                str(self._get_cached_filepath(basename))
                continue
            except FileNotFoundError:
                pass

            # FALL-THROUGH
            # -> download it
            self._download_file(
                url=f"{self.remote_url_path}/{basename}",
                dest=self.cache_dir / basename,
            )

    @staticmethod
    def _download_file(url: str, dest: Path):
        """Retrieves a file from the HTTP source and writes it to the destination.

        Raises:
            RuntimeError: if the file retrieval fails.
        """
        LOGGER.info(f"[download] getting {dest=} {url=}")

        def backoff_sleep(_attempt: int):
            """Sleep with exponential backoff."""
            sleep_duration = 2**_attempt  # Exponential backoff: 2, 4, 8 seconds...
            LOGGER.debug(f"[download] retrying in {sleep_duration}s...")
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
                    raise DownloadFailedException(
                        f"[download] failed after {cfg.REMOTE_DATA_DOWNLOAD_RETRIES} retries: {dest=} {url=}"
                    ) from e

        # Step 2: Write the file
        try:
            # NOTE: this uses the 'REMOTE_DATA_READ_TIMEOUT' timeout value, set above
            with open(dest, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        except IOError as e:
            raise DownloadFailedException(
                f"[download] failed during file write: {dest=} {url=}"
            ) from e

        # Step 3: Ensure the file was created successfully
        if dest.is_file():
            LOGGER.info(f"[download] created {dest=}")
        else:
            raise DownloadFailedException(
                f"[download] failed during file write (file is invalid): {dest=} {url=}"
            )

    def get_filepath(self, filename: str) -> str:
        """Look up filename under the local paths and the cache dir -- returns first match.

        Args:
            filename (str): file basename to look up.

        Returns:
            str: valid filename.
        """
        # validate
        if not is_filename(filename):
            raise InvalidFilenameException(
                f"Cannot retrieve {filename=} -- expected a filename without any path components.'"
            )

        # first, get file from a local dir
        try:
            return self._get_local_filepath(filename)
        except FileNotFoundError:
            pass

        # backup plan: look at cache dir
        try:
            return str(self._get_cached_filepath(filename))
        except FileNotFoundError:
            pass

        # FALL-THROUGH
        raise FileNotFoundError(filename)

    def _get_cached_filepath(self, filename: str) -> Path:
        """Look up filename on cache dir path."""
        filepath = self.cache_dir / filename
        LOGGER.info(f"[cache] trying {filepath=}")

        if not filepath.is_file():
            raise FileNotFoundError(filepath)

        LOGGER.info(f"[cache] found {filepath=}")
        return filepath

    def _get_local_filepath(self, filename: str) -> str:
        """Look up filename on local paths and return the first matching filename.

        Args:
            filename (str): the filename of the file to look up.

        Returns:
            str: the file path of the file if available
        """

        for source in self.local_dirs:
            filepath = source / filename
            LOGGER.info(f"[local] trying {filepath=}")
            if filepath.is_file():
                LOGGER.info(f"[local] found {filepath=}")
                return str(filepath)

        # FALL-THROUGH
        # -> File was not found in local paths.
        raise FileNotFoundError(filename)


def get_gcd_datastager() -> DataStager:
    """Get a DataStager instance configured for GCD files."""
    return DataStager(
        local_data_sources=cfg.LOCAL_GCD_DATA_SOURCES,
        local_subdir=cfg.LOCAL_GCD_SUBDIR,
        remote_url_path=cfg.REMOTE_GCD_DATA_SOURCE,
    )
