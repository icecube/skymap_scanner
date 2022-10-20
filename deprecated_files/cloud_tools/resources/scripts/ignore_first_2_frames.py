#!/usr/bin/env python


# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod /mnt/resources/scripts/split_GCD_and_QP.py /mnt/Run00118973.i3.zst

import sys
import os

from I3Tray import *

from icecube import icetray, dataclasses, dataio


infile = sys.argv[1]

file, ext = os.path.splitext(infile)

if ext in ['.zst', '.gz']:
    file, ext2 = os.path.splitext(file)
    ext = ext2+ext


outfile = file+'_ignored_first_2_frames'+ext


print("Reading from {}".format(infile))
print("Writing to {}".format(outfile))


class IgnoreNFrames(icetray.I3Module):
    def __init__(self, ctx):
        super(IgnoreNFrames, self).__init__(ctx)
        self.AddParameter("NFramesToIgnore",
            "The number of frames to ignore",
            0)
        self.AddOutBox("OutBox")

    def Configure(self):
        self.n_ignore = self.GetParameter("NFramesToIgnore")

    def Process(self):
        frame = self.PopFrame()
        if not frame:
            raise RuntimeError("You must not use IgnoreNFrames as a driving module")

        if self.n_ignore > 0:
            self.n_ignore -= 1
            del frame
            return
        
        self.PushFrame(frame)


tray = I3Tray()

tray.Add("I3Reader", "reader", Filename=infile)

tray.Add(IgnoreNFrames, "IgnoreNFrames",
    NFramesToIgnore=2)

tray.Add("I3Writer", "writer",
    Filename=outfile, Streams=[
        icetray.I3Frame.Geometry,
        icetray.I3Frame.Calibration,
        icetray.I3Frame.DetectorStatus,
        icetray.I3Frame.DAQ,
        icetray.I3Frame.Physics,
    ])

tray.Execute()
tray.Finish()
del tray

