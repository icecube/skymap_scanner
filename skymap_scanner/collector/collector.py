"""The Collector service."""

# fmt: off
# mypy: ignore-errors
# pylint: skip-file

import os

import numpy
from icecube import icetray

from .utils import save_GCD_frame_packet_to_file


class FindBestRecoResultForPixel(icetray.I3Module):
    def __init__(self, ctx):
        super(FindBestRecoResultForPixel, self).__init__(ctx)
        self.AddOutBox("OutBox")
        self.AddParameter("NPosVar", "Number of position variations to collect", 7)

    def Configure(self):
        self.NPosVar = self.GetParameter("NPosVar")

        self.pixelNumToFramesMap = {}

    def Physics(self, frame):
        if "SCAN_HealpixNSide" not in frame:
            raise RuntimeError("SCAN_HealpixNSide not in frame")
        if "SCAN_HealpixPixel" not in frame:
            raise RuntimeError("SCAN_HealpixPixel not in frame")
        if "SCAN_PositionVariationIndex" not in frame:
            raise RuntimeError("SCAN_PositionVariationIndex not in frame")

        nside = frame["SCAN_HealpixNSide"].value
        pixel = frame["SCAN_HealpixPixel"].value
        index = (nside,pixel)
        posVarIndex = frame["SCAN_PositionVariationIndex"].value

        if index not in self.pixelNumToFramesMap:
            self.pixelNumToFramesMap[index] = []
        self.pixelNumToFramesMap[index].append(frame)

        if len(self.pixelNumToFramesMap[index]) >= self.NPosVar:
            # print "all scans arrived for pixel", index
            bestFrame = None
            bestFrameLLH = None
            for frame in self.pixelNumToFramesMap[index]:
                if "MillipedeStarting2ndPass_millipedellh" in frame:
                    thisLLH = frame["MillipedeStarting2ndPass_millipedellh"].logl
                else:
                    thisLLH = numpy.nan
                # print "  * llh =", thisLLH
                if (bestFrame is None) or ((thisLLH < bestFrameLLH) and (not numpy.isnan(thisLLH))):
                    bestFrame=frame
                    bestFrameLLH=thisLLH

            # print "all scans arrived for pixel", index, "best LLH is", bestFrameLLH

            if bestFrame is None:
                # just push the first frame if all of them are nan
                self.PushFrame(self.pixelNumToFramesMap[index][0])
            else:
                self.PushFrame(bestFrame)

            del self.pixelNumToFramesMap[index]

    def Finish(self):
        if len(self.pixelNumToFramesMap) == 0:
            return

        print("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
        print((self.pixelNumToFramesMap))
        print("**** WARN ****  --  END")


class CollectRecoResults(icetray.I3Module):
    def __init__(self, ctx):
        super(CollectRecoResults, self).__init__(ctx)
        self.AddParameter("state_dict", "The state_dict", None)
        self.AddParameter("event_id", "The event_id", None)
        self.AddParameter("cache_dir", "The cache_dir", None)
        self.AddOutBox("OutBox")

    def Configure(self):
        self.state_dict = self.GetParameter("state_dict")
        self.event_id = self.GetParameter("event_id")
        self.cache_dir = self.GetParameter("cache_dir")

        self.this_event_cache_dir = os.path.join(self.cache_dir, self.event_id)

    def Physics(self, frame):
        if "SCAN_HealpixNSide" not in frame:
            raise RuntimeError("SCAN_HealpixNSide not in frame")
        if "SCAN_HealpixPixel" not in frame:
            raise RuntimeError("SCAN_HealpixPixel not in frame")
        if "SCAN_PositionVariationIndex" not in frame:
            raise RuntimeError("SCAN_PositionVariationIndex not in frame")

        nside = frame["SCAN_HealpixNSide"].value
        pixel = frame["SCAN_HealpixPixel"].value
        index = (nside,pixel)

        if "MillipedeStarting2ndPass" not in frame:
            raise RuntimeError("\"MillipedeStarting2ndPass\" not found in reconstructed frame")
        if "MillipedeStarting2ndPass_millipedellh" not in frame:
            llh = numpy.nan
            # raise RuntimeError("\"MillipedeStarting2ndPass_millipedellh\" not found in reconstructed frame")
        else:
            llh = frame["MillipedeStarting2ndPass_millipedellh"].logl

        if nside not in self.state_dict["nsides"]:
            self.state_dict["nsides"][nside] = {}

        if pixel in self.state_dict["nsides"][nside]:
            raise RuntimeError("NSide {0} / Pixel {1} is already in state_dict".format(nside, pixel))
        self.state_dict["nsides"][nside][pixel] = dict(frame=frame, llh=llh)

        # save this frame to the disk cache

        nside_dir = os.path.join(self.this_event_cache_dir, "nside{0:06d}".format(nside))
        if not os.path.exists(nside_dir):
            os.mkdir(nside_dir)
        pixel_file_name = os.path.join(nside_dir, "pix{0:012d}.i3".format(pixel))

        # print " - saving pixel file {0}...".format(pixel_file_name)
        save_GCD_frame_packet_to_file([frame], pixel_file_name)

        self.PushFrame(frame)


def main() -> None:
    """Start up Collector service."""
    tray.AddModule(FindBestRecoResultForPixel, "FindBestRecoResultForPixel")
    tray.AddModule(CollectRecoResults, "CollectRecoResults",
        state_dict = state_dict,
        event_id = event_id_string,
        cache_dir = cache_dir
    )


if __name__ == "__main__":
    main()
