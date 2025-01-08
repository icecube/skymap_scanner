"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors
# fmt: off

from typing import Final

from . import splinempe
from . import RecoInterface

class SplineMPEPointed(splinempe.SplineMPE):

    def __init__(self):
        super().__init__()
        self.pointing_dir_names = ["OnlineL2_SplineMPE", "l2_online_SplineMPE"]

RECO_CLASS: Final[type[RecoInterface]] = SplineMPEPointed
