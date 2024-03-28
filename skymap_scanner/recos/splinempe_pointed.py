from splinempe import SplineMPE
from icecube import astro
from icecube.icetray import I3Frame
from typing import List

class SplineMPE_pointed(SplineMPE):

    def __init__(self):
        super().__init__()
        self.use_online_ra_dec = True
        self.particle_name_possibilities = ["OnlineL2_SplineMPE", "l2_online_SplineMPE"]