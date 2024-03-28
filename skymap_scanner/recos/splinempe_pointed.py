from splinempe import SplineMPE
from icecube import astro
from icecube.icetray import I3Frame

class SplineMPE_pointed(SplineMPE):

    def __init__(self):
        super().__init__()
        self.use_online_ra_dec = True
        self.particle_name_possibilities = ["OnlineL2_SplineMPE", "l2_online_SplineMPE"]
    
    def get_particle_name_possibilities(self):
        return self.particle_name_possibilities