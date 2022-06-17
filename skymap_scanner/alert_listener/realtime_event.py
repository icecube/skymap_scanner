import base64
import logging
import pickle
import zlib

from icecube import icetray

from skymap_scanner.alert_listener.event import ICEvent, FramePacket


class RealtimeEvent:
    """
    The implementation of this class assumes that the event dictionary is structured according to the new (2018) data format, with the data frames accessible under key value/data/frames. The pre-2018 format has frames in value/data and is supported in IceTray (see `full_event_followup/python/frame_packet_to_i3live_json.py`). The original `skymap_scanner` code assumed the new format, so the old one is not meant to be supported here (unless required).
    """

    def __init__(self, event, extract=False) -> None:
        self.event_dict = event
        self.logger = logging.getLogger(__name__)

        if extract:
            self.event = ICEvent(id=self.get_uid(), frame_packet=self.extract_frames())
            del self.event_dict["value"]["data"]["frames"]

    def get_packed_frames(self):
        return self.event_dict["value"]["data"]["frames"]

    def get_message_time(self):
        return self.event_dict["time"]

    def get_uid(self):
        return self.event_dict["value"]["data"]["unique_id"]

    def get_run(self):
        return self.event_dict["value"]["data"]["run_id"]

    def get_event_number(self):
        return self.event_dict["value"]["data"]["event_id"]

    def get_stem(self):
        """
        filename stem based on evt and run number
        in origin this was based on a hash of event['time']
        to be verified if this new approach is equally robust
        """
        uid = self.get_uid()
        # dashes are preferred to dots in directory names
        stem = uid.replace(".", "-")

        return stem

    def get_alert_streams(self):
        # previous code used this for no apparent good reason:
        # [str(x) for x in event["value"]["streams"]]
        return self.event["value"]["streams"]

    def get_event(self) -> ICEvent:
        return self.event

    def extract_frames(self) -> FramePacket:
        """
        This method replaces:
            full_event_followup.i3live_json_to_frame_packet(
                json.dumps(self.event), pnf_framing=True)
        The frame_list from the realtime event is a list of tuples (each tuple is a python list). Each tuple contains a frame ID (G, C, D, Q, P) associated to packed I3 frame data.
        """
        packed_frames = self.get_packed_frames()

        frames = list()
        for frame_tuple in packed_frames:
            frame = self.extract_frame_tuple(frame_tuple)
            frames.append(frame)
        self.frames = frames

        return FramePacket(frames)

    def extract_frame_tuple(self, frame_tuple):
        """
        Stripped-down code from `icetray/full_event_followup/python/frame_packet_to_i3live_json.py`

        This functions extract the frame tuple and performs some integrity checks. The tuple must not have more than two elements (id and data). The packed frame data is a pickled I3 object (I3Frame) compressed with zlib and encoded in a base64 string (need to reverse that).
        """

        # 1. check integrity

        if len(frame_tuple) == 2:
            frame_id, frame_data = frame_tuple
        else:
            raise ValueError("Frame tuple has more than two values")

        # 2. decode and decompress

        decompressed_data = zlib.decompress(base64.b64decode(frame_data))

        del frame_data

        # 3. unpickle

        frame_object = self.unpickle_frame(decompressed_data)

        del decompressed_data

        # 4. check consistency

        if frame_object.Stop.id != frame_id:
            raise ValueError(
                f"Frame ID mismatch between content - frame {frame_object.Stop.id} - and dictionary has {frame_id}"
            )

        return frame_object

    def unpickle_frame(self, decompressed_data):
        try:
            frame_object = pickle.loads(decompressed_data, encoding="bytes")
            self.logger.debug("Frame unpickled with byte encoding")
        except TypeError:  # this is the python 2 version
            frame_object = pickle.loads(decompressed_data)
            self.logger.warning("Frame unpickled with default encoding")
        return frame_object
