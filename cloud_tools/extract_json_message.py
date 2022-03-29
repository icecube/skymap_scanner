from __future__ import print_function
from __future__ import absolute_import

import json

from icecube import icetray, full_event_followup

def extract_json_message(json_data):
    # extract the packet
    frame_packet = full_event_followup.i3live_json_to_frame_packet(json.dumps(json_data), pnf_framing=True)

    # we assume we get GCDQP here
    if frame_packet[3].Stop != icetray.I3Frame.DAQ:
        raise RuntimeError("Expected a DAQ frame as the 4th entry in the frame packet")
    
    # The frame packet generator renames I3EventHeader in Q frames to QI3EventHeader.
    # Revert that.
    if ("QI3EventHeader" in frame_packet[3]) and ("I3EventHeader" not in frame_packet[3]):
        frame_packet[3].Rename("QI3EventHeader", "I3EventHeader")

    return frame_packet
