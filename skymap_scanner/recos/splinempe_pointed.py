"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors

from splinempe import SplineMPE     # type: ignore[import]
from icecube import astro           # type: ignore[import]
from icecube.icetray import I3Frame # type: ignore[import]
from typing import List             # type: ignore[import]

class SplineMPE_pointed(SplineMPE):

    def __init__(self):
        super().__init__()
        self.use_online_ra_dec = True