"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors

from . import splinempe  
from icecube import astro           
from icecube.icetray import I3Frame
from typing import Final, List
from . import RecoInterface       

class SplineMPE_pointed(splinempe.SplineMPE):

    def __init__(self):
        super().__init__()
        self.use_online_ra_dec = True

RECO_CLASS: Final[type[RecoInterface]] = SplineMPE_pointed