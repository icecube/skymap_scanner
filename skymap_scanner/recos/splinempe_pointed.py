"""IceTray segment for a pointed splinempe reco."""

# mypy: ignore-errors
 
from typing import Final, Tuple, Union, Optional

from icecube.icetray import I3Frame
from icecube import astro

from . import splinempe 
from . import RecoInterface       

class SplineMPE_pointed(splinempe.SplineMPE):

    def __init__(self):
        super().__init__()

def get_pointing_info(
    p_frame: Optional[I3Frame]
) -> Tuple[float, Union[Tuple[float, float], None]]:
ang_dist = 3.5
particle_name_possibilities = ["OnlineL2_SplineMPE", "l2_online_SplineMPE"]
for particle_name in particle_name_possibilities:
    if particle_name in p_frame.keys():
        online_dir = p_frame[particle_name].dir
        online_ra_dec = astro.dir_to_equa(
            online_dir.zenith,
            online_dir.azimuth,
            p_frame["I3EventHeader"].start_time.mod_julian_day_double
        )
return ang_dist, online_ra_dec

RECO_CLASS: Final[type[RecoInterface]] = SplineMPE_pointed