from icecube import full_event_folluwup
import json


class EventProcessor():
    def __init__(self):
        self.log = logging.getLogger(__name__)

    def parse(self, event_dict):
        event_json = json.dumps(event_dict)
        frame_packet = full_event_followup.i3live_json_to_frame_packet(
            event_json, pnf_framing=True)
        return frame_packet
