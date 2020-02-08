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


outfile_GCD = file+'_GCD'+ext
outfile_QP = file+'_QP'+ext


print("Reading from {}".format(infile))
print("Writing GCDQ to {}".format(outfile_GCD))
print("Writing QP to {}".format(outfile_QP))


tray = I3Tray()

tray.Add("I3Reader", "reader", Filename=infile)

tray.Add("I3Writer", "writer_GCD",
    Filename=outfile_GCD, Streams=[
        icetray.I3Frame.Geometry,
        icetray.I3Frame.Calibration,
        icetray.I3Frame.DetectorStatus,
    ])

tray.Add("I3Writer", "writer_QP",
    Filename=outfile_QP, Streams=[
        icetray.I3Frame.DAQ,
        icetray.I3Frame.Physics,
    ])

tray.Execute()
tray.Finish()
del tray

