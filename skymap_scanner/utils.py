"""Generic utility functions."""

# fmt: off
# pylint: skip-file

import dataclasses as dc
import hashlib
import os
from typing import Any, Dict, List, Tuple

from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]

from . import config

StateDict = Dict[str, Any]


def get_event_mjd(state_dict):
    if "GCDQp_packet" not in state_dict:
        raise RuntimeError("GCDQp_packet not found in state_dict")
    frame_packet = state_dict["GCDQp_packet"]

    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Physics and p_frame.Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("no p-frame found at the end of the GCDQp packet")
    if "I3EventHeader" not in p_frame:
        raise RuntimeError("No I3EventHeader in p-frame")
    time = p_frame["I3EventHeader"].start_time

    return time.mod_julian_day_double


def create_event_id(run_id, event_id):
    return "run{0:08d}.evt{1:012d}.HESE".format(run_id, event_id)


def parse_event_id(event_id_string):
    parts = event_id_string.split('.')
    if len(parts) != 3:
        raise RuntimeError("event ID must have 3 parts separated by '.'")

    if not parts[0].startswith("run"):
        raise RuntimeError("event ID run part does not start with \"run\"")
    if not parts[1].startswith("evt"):
        raise RuntimeError("event ID event part does not start with \"evt\"")

    run = int(parts[0][3:])
    event = int(parts[1][3:])
    evt_type = parts[2]
    return (run, event, evt_type)


def load_GCD_frame_packet_from_file(filename, filestager=None):
    read_url = filename
    for GCD_base_dir in config.GCD_BASE_DIRS:
        potential_read_url = os.path.join(GCD_base_dir, filename)
        if os.path.isfile( potential_read_url ):
            read_url = potential_read_url
            break

    if filestager is not None:
        read_url_handle = filestager.GetReadablePath( read_url )
    else:
        read_url_handle = read_url

    frame_packet = []
    i3f = dataio.I3File(str(read_url_handle),'r')
    while True:
        if not i3f.more():
            return frame_packet
        frame = i3f.pop_frame()
        frame_packet.append(frame)

    del read_url_handle


def save_GCD_frame_packet_to_file(
    frame_packet: List[icetray.I3Frame],
    filename: str
) -> None:
    i3f = dataio.I3File(filename,'w')
    for frame in frame_packet:
        i3f.push(frame)
    i3f.close()
    del i3f


def hash_frame_packet(frame_packet):
    m = hashlib.sha1()
    for frame in frame_packet:
        m.update(frame.dumps())
    return m.hexdigest()


def rewrite_frame_stop(input_frame, new_stream):
    input_frame.purge() # deletes all non-native items

    for key in list(input_frame.keys()):
        input_frame.change_stream(key, new_stream)

    new_frame = icetray.I3Frame(new_stream)
    new_frame.merge(input_frame)
    del input_frame

    return new_frame


def extract_MC_truth(state_dict):
    if "GCDQp_packet" not in state_dict:
        raise RuntimeError("GCDQp_packet not found in state_dict")
    frame_packet = state_dict["GCDQp_packet"]

    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Stream('p') and p_frame.Stop != icetray.I3Frame.Physics:
        raise RuntimeError("last frame of GCDQp is neither Physics not 'p'")

    q_frame = frame_packet[-2]
    if q_frame.Stop != icetray.I3Frame.DAQ:
        raise RuntimeError("second to last frame of GCDQp is not type Q")

    if "I3MCTree_preMuonProp" not in q_frame:
        return state_dict
    mc_tree = q_frame["I3MCTree_preMuonProp"]

    # find the muon
    muon = None
    for particle in mc_tree:
        if particle.type not in [dataclasses.I3Particle.ParticleType.MuPlus, dataclasses.I3Particle.ParticleType.MuMinus]: continue
        if muon is not None:
            print("More than one muon in MCTree")
            if particle.energy < muon.energy: continue
        muon = particle

    if muon is None:
        # must be NC
        return state_dict

    # get event time
    mjd = get_event_mjd(state_dict)

    # convert to RA and dec
    ra, dec = astro.dir_to_equa( muon.dir.zenith, muon.dir.azimuth, mjd )
    ra = float(ra)
    dec = float(dec)
    dec = dec

    state_dict['MCradec'] = (ra, dec)

    return state_dict


# fmt: on


def pixel_to_tuple(pixel: icetray.I3Frame) -> Tuple[int, int, int]:
    """Get a tuple representing a pixel PFrame for logging."""
    return (
        pixel["SCAN_HealpixNSide"].value,
        pixel["SCAN_HealpixPixel"].value,
        pixel["SCAN_PositionVariationIndex"].value,
    )


@dc.dataclass
class PixelReco:
    nside: int
    pixel: int
    llh: float
    reco_losses_inside: float
    reco_losses_total: float
    pos_var_index: int
    id_tuple: Tuple[int, int, int] = dc.field(init=False, repr=False)
    position: dataclasses.I3Position
    time: float
    energy: float

    def __post_init__(self) -> None:
        self.id_tuple = (self.nside, self.pixel, self.pos_var_index)


# fmt: off
