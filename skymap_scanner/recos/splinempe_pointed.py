"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors
 
from typing import Final

from . import splinempe 
from . import RecoInterface       

class SplineMPE_pointed(splinempe.SplineMPE):

    def __init__(self):
        super().__init__()

RECO_CLASS: Final[type[RecoInterface]] = SplineMPE_pointed