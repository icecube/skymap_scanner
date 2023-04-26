from pathlib import Path
from typing import Dict

from skymap_scanner.utils.data_handling import DataStager
from skymap_scanner import config as cfg


local_file_list = []

# We first get a list of all local files
for path in cfg.LOCAL_DATA_SOURCES:
    subpath = path / cfg.LOCAL_SPLINE_SUBDIR
    directory_content = subpath.glob("*")
    for path in directory_content:
        if path.is_file():
            # skip directories
            local_file_list.append(path.name)  # store name (basename)

remote_file_list = ["README"]  # files only expected to be available remotely

datastager = DataStager(
    local_paths=cfg.LOCAL_DATA_SOURCES,
    local_subdir=cfg.LOCAL_SPLINE_SUBDIR,
    remote_path=f"{cfg.REMOTE_DATA_SOURCE}/{cfg.REMOTE_SPLINE_SUBDIR}",
)

datastager.stage_files(local_file_list)
datastager.stage_files(remote_file_list)

# ensure that filepaths can be retrieved for all local files
local_filepaths: Dict[str, str] = dict()
for filename in local_file_list:
    print(f"Testing local file: {filename}.")
    local_filepaths[filename] = datastager.get_local_filepath(filename)
    assert local_filepaths[filename] == datastager.get_filepath(filename)
    print(f"File available at {local_filepaths[filename]}.")

for filename in remote_file_list:
    print(f"Testing staging of remote file: {filename}")
    filepath: str = datastager.get_filepath(filename)
    print(f"File available at {filepath}.")
