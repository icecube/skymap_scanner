#!/usr/bin/env python

import sys
import os
import copy

from I3Tray import *

from icecube import icetray, dataclasses, dataio

import numpy
import healpy


infile = sys.argv[1]

file, ext = os.path.splitext(infile)

if ext in ['.zst', '.gz']:
    file, ext2 = os.path.splitext(file)
    ext = ext2+ext

outfile_fixed_dec = file+'_fixed_dec'+ext

print("Reading from {}".format(infile))
print("Writing to {}".format(outfile_fixed_dec))


tray = I3Tray()

tray.Add("I3Reader", "reader", Filename=infile)

# work on P-frames only
def fix_pixel_num(frame):
    nside = frame["SCAN_HealpixNSide"].value
    pixel = frame["SCAN_HealpixPixel"].value
    posvar = frame["SCAN_PositionVariationIndex"].value
    header = frame["I3EventHeader"]

    # we used to do this to go from pixel to dec/ra:
    dec, ra = healpy.pix2ang(nside, pixel)
    dec = dec - numpy.pi/2.

    # this is what we *should* have done:
    # dec = numpy.pi/2. - dec

    new_pixel = healpy.ang2pix(nside, numpy.pi/2.-dec, ra)
    
    # --- sanity check
    # (this is how we *want* this to be converted. Make sure the above did the right thing)
    new_dec, new_ra = healpy.pix2ang(nside, new_pixel)
    new_dec = numpy.pi/2. - new_dec
    if abs(new_dec - dec) > 1e-7:
        raise RuntimeError("Logic error in pixel conversion. new_dec={}, dec={}".format(new_dec, dec))
    # --- end sanity check

    new_header = copy.copy(header)
    new_header.sub_event_id = new_pixel
    new_header.sub_event_stream = "SCAN_nside%04u_pixel%04u_posvar%04u" % (nside, new_pixel, posvar)
    
    del frame["SCAN_HealpixPixel"]
    frame["SCAN_HealpixPixel"] = icetray.I3Int(new_pixel)

    del frame["I3EventHeader"]
    frame["I3EventHeader"] = new_header
    
    #print("Replaced [I3EventHeader.sub_event_stream]\"{}\" with \"{}\" and [SCAN_HealpixPixel]\"{}\" with \"{}\".".format( header.sub_event_stream, new_header.sub_event_stream, pixel, new_pixel ))
tray.Add(fix_pixel_num, "fix_pixel_num")

tray.Add("I3Writer", "writer_fixed_dec",
    Filename=outfile_fixed_dec, Streams=[
        icetray.I3Frame.Geometry,
        icetray.I3Frame.Calibration,
        icetray.I3Frame.DetectorStatus,
        icetray.I3Frame.DAQ,
        icetray.I3Frame.Stream('p'),
        icetray.I3Frame.Physics,
    ])

tray.Execute()
tray.Finish()
del tray

