"""Generic utility functions."""

# fmt: off
# pylint: skip-file

import hashlib
import json
import os
from pprint import pformat
from typing import Any, List, Optional, Tuple

from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]

from .. import config as cfg
from . import LOGGER


def pow_of_two(value: Any) -> int:
    """Return int-cast of `value` if it is an integer power of two (2^n)."""
    intval = int(value)  # -> ValueError
    # I know, I know, no one likes bit shifting... buuuut...
    if (intval != 0) and (intval & (intval - 1) == 0):
        return intval
    raise ValueError(f"Not a power of two (2^n) {value}")


def pyobj_to_string_repr(obj: Any) -> str:
    """Get the string repr of obj, an indented JSON if possible."""
    try:
        return json.dumps(obj, indent=4)
    except:  # noqa: E722
        pass
    return pformat(obj, indent=4)


def get_event_mjd(frame_packet: List[icetray.I3Frame]) -> float:
    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Physics and p_frame.Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("no p-frame found at the end of the GCDQp packet")
    if "I3EventHeader" not in p_frame:
        raise RuntimeError("No I3EventHeader in p-frame")
    time = p_frame["I3EventHeader"].start_time

    return time.mod_julian_day_double  # type: ignore[no-any-return]


def load_GCD_frame_packet_from_file(filename, filestager=None):
    read_url = filename
    for GCD_base_dir in cfg.GCD_BASE_DIRS:
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


def extract_MC_truth(frame_packet: List[icetray.I3Frame]) -> Optional[Tuple[float, float]]:

    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Stream('p') and p_frame.Stop != icetray.I3Frame.Physics:
        raise RuntimeError("last frame of GCDQp is neither Physics not 'p'")

    q_frame = frame_packet[-2]
    if q_frame.Stop != icetray.I3Frame.DAQ:
        raise RuntimeError("second to last frame of GCDQp is not type Q")

    if "I3MCTree_preMuonProp" not in q_frame:
        return None
    mc_tree = q_frame["I3MCTree_preMuonProp"]

    # find the muon
    muon = None
    for particle in mc_tree:
        if particle.type not in [dataclasses.I3Particle.ParticleType.MuPlus, dataclasses.I3Particle.ParticleType.MuMinus]: continue
        if muon is not None:
            LOGGER.debug("More than one muon in MCTree")
            if particle.energy < muon.energy: continue
        muon = particle

    if muon is None:
        # must be NC
        return None

    # get event time
    mjd = get_event_mjd(frame_packet)

    # convert to RA and dec
    ra, dec = astro.dir_to_equa( muon.dir.zenith, muon.dir.azimuth, mjd )
    ra = float(ra)
    dec = float(dec)

    return (ra, dec)
