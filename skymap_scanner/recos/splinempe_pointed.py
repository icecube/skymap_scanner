"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors
 
from typing import Final

from . import splinempe 
from . import RecoInterface
from .. import config


class SplineMPEPointed(splinempe.SplineMPE):

    def __init__(self, realtime_format_version: str):
        super().__init__(realtime_format_version)
        self.pointing_dir_name = config.INPUT_KEY_NAMES_MAP.get(
            realtime_format_version,
            config.DEFAULT_INPUT_KEY_NAMES).l2_splinempe


RECO_CLASS: Final[type[RecoInterface]] = SplineMPEPointed
