"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors
 
from typing import Final, Tuple, Union

from icecube.icetray import I3Frame
from icecube import astro

from . import splinempe 
from . import RecoInterface       

class SplineMPE_pointed(splinempe.SplineMPE):

    particle_name_possibilities = ["OnlineL2_SplineMPE", "l2_online_SplineMPE"]

    def __init__(self):
        super().__init__()
        self.use_pointing = True

RECO_CLASS: Final[type[RecoInterface]] = SplineMPE_pointed