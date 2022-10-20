#!/usr/bin/env python

import sys
import os

from I3Tray import *

from icecube import icetray, dataclasses, dataio


infile = sys.argv[1]

file, ext = os.path.splitext(infile)

if ext in ['.zst', '.gz']:
    file, ext2 = os.path.splitext(file)
    ext = ext2+ext


#outfile_GCDQp = file+'_GCDQp'+ext
outfile_P = file+'_P'+ext


print("Reading from {}".format(infile))
#print("Writing GCDQp to {}".format(outfile_GCDQp))
print("Writing P to {}".format(outfile_P))


tray = I3Tray()

tray.Add("I3Reader", "reader", Filename=infile)

# tray.Add("I3Writer", "writer_GCDQp",
#     Filename=outfile_GCDQp, Streams=[
#         icetray.I3Frame.Geometry,
#         icetray.I3Frame.Calibration,
#         icetray.I3Frame.DetectorStatus,
#         icetray.I3Frame.DAQ,
#         icetray.I3Frame.Stream('p'),
#     ])

tray.Add("I3Writer", "writer_P",
    Filename=outfile_P, Streams=[
        icetray.I3Frame.Physics,
    ])

tray.Execute()
tray.Finish()
del tray

