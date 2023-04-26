from skymap_scanner.utils.data_handling import DataStager
from skymap_scanner import config as cfg

datastager = DataStager(
    local_paths=cfg.LOCAL_DATA_SOURCES,
    local_subdir=cfg.LOCAL_SPLINE_SUBDIR,
    remote_path=f"{cfg.REMOTE_DATA_SOURCE}/{cfg.REMOTE_SPLINE_SUBDIR}",
)

FILE_LIST = ["README", "ems_mie_z20_a10.abs.fits"]

datastager.stage_files(FILE_LIST)

for filename in FILE_LIST:
    filepath: str = datastager.get_filepath(filename)
    print(f"{filename} is available at {filepath}.")
