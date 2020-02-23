#!/usr/bin/env python

# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod /mnt/extract_single_event.py /mnt/Level2pass2_IC86.2012_data_Run00120244_0601_1_20_GCD.i3.zst /mnt/Level2pass2_IC86.2012_data_Run00120244_Subrun00000000_00000058.i3.zst 21476686

import sys
import os
import copy

from I3Tray import *

from icecube import icetray, dataclasses, dataio

import numpy
import healpy


infiles = sys.argv[1:-1]
eventnum = int(sys.argv[-1])

if len(infiles) == 0:
    raise RuntimeError("Must provide an input file name")

if len(infiles) == 1:
    base_infile = infiles[0]
else:
    base_infile = infiles[1]

file, ext = os.path.splitext(base_infile)

if ext in ['.zst', '.gz']:
    file, ext2 = os.path.splitext(file)
    ext = ext2+ext

outfile_fixed_dec = file+'_event{}'.format(eventnum)+ext

print("Reading from {}".format(infiles))
print("Writing to {}".format(outfile_fixed_dec))

tray = I3Tray()

tray.Add("I3Reader", "reader", FilenameList=infiles)

def keep_QP_event_num(frame, event_num, p_frame_splits=['InIceSplit']):
    header = frame['I3EventHeader']
    if header.event_id != event_num:
        return False
    
    if frame.Stop != icetray.I3Frame.Physics:
        return True
    
    # for P-frames check the "split"
    if header.sub_event_stream not in p_frame_splits:
        return False
    
    return True
tray.Add(keep_QP_event_num, "keep_QP_event_num",
    Streams=[icetray.I3Frame.DAQ, icetray.I3Frame.Physics],
    event_num=eventnum)

tray.Add("I3Writer", "writer",
    Filename=outfile_fixed_dec, Streams=[
        icetray.I3Frame.Geometry,
        icetray.I3Frame.Calibration,
        icetray.I3Frame.DetectorStatus,
        icetray.I3Frame.DAQ,
        icetray.I3Frame.Physics,
    ])

tray.Execute()
tray.Finish()
del tray

