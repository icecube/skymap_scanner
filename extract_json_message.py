from __future__ import print_function
from __future__ import absolute_import

import json

from icecube import full_event_followup

def extract_json_message(json_data):
    # extract the packet
    frame_packet = full_event_followup.i3live_json_to_frame_packet(json.dumps(json_data), pnf_framing=True)

    return frame_packet
