import base64
import logging
import pickle
import zlib

from icecube import icetray

from utils import rewrite_frame_stop


class RealtimeEvent:
    """
    The implementation of this class assumes that the event dictionary is structured according to the new (2018) data format, with the data frames accessible under key value/data/frames. The pre-2018 format has frames in value/data and is supported in IceTray (see `full_event_followup/python/frame_packet_to_i3live_json.py`). The original `skymap_scanner` code assumed the new format, so the old one is not meant to be supported here (unless required).
    """

    def __init__(self, event, extract_frames=False) -> None:
        self.event = event
        self.logger = logging.getLogger(__name__)

        if extract_frames:
            self.frame_packet = self.extract_frame_packet()
            del self.event["value"]["data"]["frames"]

    def get_frame_list(self):
        return self.event["value"]["data"]["frames"]

    def get_message_time(self):
        return self.event["time"]

    def get_uid(self):
        return self.event["value"]["data"]["unique_id"]

    def get_run(self):
        return self.event["value"]["data"]["run_id"]

    def get_event_number(self):
        return self.event["value"]["data"]["event_id"]

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

    def extract_frame_packet(self):
        """
        This method replaces:
            full_event_followup.i3live_json_to_frame_packet(
                json.dumps(self.event), pnf_framing=True)
        """
        frame_list = self.get_frame_list()
        return FramePacket(frame_list)

    def get_physics_frame(self):
        return self.frame_packet.get_physics_frame()


class FramePacket:

    NFRAMES_MIN = 5  # G C D Q P

    def __init__(self, frame_list) -> None:

        self.logger = logging.getLogger(__name__)

        frames = list()

        """
        The frame_list from the realtime event is a list of tuples (each tuple is a python list). Each tuple contains a frame ID (G, C, D, Q, P) associated to packed I3 frame data.
        """
        for frame_tuple in frame_list:
            frame = self.extract_frame_tuple(frame_tuple)
            frames.append(frame)

        self.frames = frames

        self.ensure_integrity()

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, index):
        return self.frames[index]

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

    def ensure_integrity(self):
        fp_len = len(self.frames)

        if fp_len < self.NFRAMES_MIN:
            raise ValueError(
                f"Frame packet has size {fp_len}, less than the required minimum {self.NFRAMES_MIN} frames (G, C, D, Q, P)"
            )

        if self.frames[-1].Stop != icetray.I3Frame.Physics:
            if self.frames[-1].Stop == icetray.I3Frame.Stream("p"):
                # compatibility with legacy IceTray versions
                self.logger.warning(
                    "Frame packet ends with frame of type 'p' and needs to be rewrited."
                )
                self.frames[-1] = rewrite_frame_stop(
                    self.frames[-1], icetray.I3Frame.Stream("P")
                )

            else:
                raise ValueError("Frame packet does not end with a Physics frame")

    def get_physics_frame(self):
        return self.frames[-1]
