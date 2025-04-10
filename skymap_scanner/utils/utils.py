"""Generic utility functions."""

# fmt: off
# pylint: skip-file

import hashlib
import json
import logging
from pprint import pformat
from typing import Any, List, Optional, Tuple

from icecube import (  # type: ignore[import-not-found]
    astro,
    dataclasses,
    dataio,
    icetray,
)

LOGGER = logging.getLogger(__name__)


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


def load_framepacket_from_file(filename : str) -> List[icetray.I3Frame]:
    """Loads an I3 file provided a filename and returns a list of I3Frame
    objects (frame packet)"""
    # Legacy code used to loop over GCD_BASE_DIRS.
    # Now it is assumed that filename points to a valid GCD file.
    frame_packet: icetray.I3Frame = []

    i3f = dataio.I3File(filename,'r')
    while True:
        if not i3f.more():
            return frame_packet
        frame = i3f.pop_frame()
        frame_packet.append(frame)

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
        if particle.type not in [dataclasses.I3Particle.ParticleType.MuPlus, dataclasses.I3Particle.ParticleType.MuMinus]:
            continue
        if muon is not None:
            LOGGER.debug("More than one muon in MCTree")
            if particle.energy < muon.energy:
                continue
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
