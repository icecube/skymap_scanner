import logging
from icecube import icetray
from skymap_scanner.utils import rewrite_frame_stop

class ICEvent:
    def __init__(self, id, frame_packet):
        self.id = id
        self.frame_packet = frame_packet
        pass

    def get_frame_packet(self):
        return self.frame_packet

    def get_physics_frame(self):
        # NOTE: metadata available in I3EventHeader / run_id, header.event_id could be checked against id
        return self.frame_packet.get_physics()


class FramePacket:

    NFRAMES_MIN = 5  # G C D Q P

    def __init__(self, frames) -> None:

        self.frames = frames
        self.logger = logging.getLogger(__name__)

        """
        Perform integrity and consistency checks.
        """
        self.check_size()
        self.check_physics()

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, index):
        return self.frames[index]

    def check_size(self):
        fp_len = len(self.frames)

        if fp_len < self.NFRAMES_MIN:
            raise ValueError(
                f"Frame packet has size {fp_len}, less than the required minimum {self.NFRAMES_MIN} frames (G, C, D, Q, P)"
            )

    def check_physics(self):
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

        if "I3EventHeader" not in self.frames[-1]:
            raise ValueError("No I3EventHeader in Physics frame")

    def get_physics(self):
        return self.frames[-1]

    def get_geometry(self):
        return self.frames[0]

    def has_gcd(self) -> bool:
        geometry = self.get_geometry()
        return ("I3Geometry" in geometry) or ("I3GeometryDiff" in geometry)

    def set_gcd(self, gcd_packet) -> None:
        for i in (0, 1, 2): # G C D
            self.frames[i] = gcd_packet[i]