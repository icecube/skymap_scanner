"""Tests for file-staging logic."""

import logging
from typing import Dict

from skymap_scanner import config as cfg
from skymap_scanner.utils.data_handling import DataStager, DownloadFailedException

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_file_staging() -> None:

    # Build list of all local files.
    local_file_list = []
    for path in cfg.LOCAL_DATA_SOURCES:
        subpath = path / cfg.LOCAL_SPLINE_SUBDIR
        directory_content = subpath.glob("*")
        for path in directory_content:
            if path.is_file():  # skip directories
                local_file_list.append(path.name)  # store filename without path

    # Declare at least one filename only expected to be available remotely.
    remote_file_list = ["README"]

    # Declare at least one filename that does not exist.
    invalid_file_list = ["NONEXISTENT_FILE"]

    datastager = DataStager(
        local_data_sources=cfg.LOCAL_DATA_SOURCES,
        local_subdir=cfg.LOCAL_SPLINE_SUBDIR,
        remote_url_path=f"{cfg.REMOTE_DATA_SOURCE}/{cfg.REMOTE_SPLINE_SUBDIR}",
    )

    # test stage_files()
    # -> OK
    for file_list in [local_file_list, remote_file_list]:
        datastager.stage_files(file_list)
    # -> ERROR
    try:
        datastager.stage_files(invalid_file_list)
    except Exception as e:
        assert isinstance(e, DownloadFailedException)
        assert f"failed after {cfg.REMOTE_DATA_DOWNLOAD_RETRIES} retries: " in str(e)

    # ensure that filepaths can be retrieved for all local files
    local_filepaths: Dict[str, str] = dict()
    for filename in local_file_list:
        logger.debug(f"Testing local file: {filename}.")
        local_filepaths[filename] = datastager._get_local_filepath(filename)
        assert local_filepaths[filename] == datastager.get_filepath(filename)
        logger.debug(f"File available at {local_filepaths[filename]}.")

    for filename in remote_file_list:
        logger.debug(f"Testing staging of remote file: {filename}")
        filepath: str = datastager.get_filepath(filename)
        logger.debug(f"File available at {filepath}.")

    for filename in invalid_file_list:
        logger.debug(f"Testing staging of remote file: {filename}")
        try:
            filepath = datastager.get_filepath(filename)
        except FileNotFoundError:
            logger.debug("File not available as expected.")
        else:
            assert 0  # we shouldn't get here!


if __name__ == "__main__":
    test_file_staging()
