#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py3-v4.1.0/icetray-start
#METAPROJECT /cvmfs/icecube.opensciencegrid.org/py3-v4.1.0/RHEL_7_x86_64/metaprojects/combo/stable

#!/usr/bin/env python

import sys
import os
import copy
import glob

from I3Tray import *

from icecube import icetray, dataclasses, dataio

def find_first_event_id(filename):
    f = dataio.I3File(filename, 'r')
    while f.more():
        fr = f.pop_frame()
        if fr.Stop != icetray.I3Frame.Physics and fr.Stop != icetray.I3Frame.DAQ:
            continue
        if "I3EventHeader" not in fr:
            continue
        event_id = fr["I3EventHeader"].event_id
        f.close()
        del f
        return event_id
    f.close()
    raise RuntimeError("No event ID found in {}".format(filename))
    return None

# first, find all run files and the GCD file in the input directory
indir = sys.argv[1]
eventnum = int(sys.argv[2])

# find the GCD file
GCD_file = glob.glob(os.path.join(indir, "Level2_*_GCD.i3.zst"))
if len(GCD_file) == 0:
    raise RuntimeError("No Level2 GCD file found in directory {}".format(indir))
if len(GCD_file) > 1:
    raise RuntimeError("More than one GCD file found in directory {}".format(indir))
GCD_file = GCD_file[0]
print("Using GCD file {}".format(GCD_file))

# find the correct run
run_files = sorted(glob.glob(os.path.join(indir, "Level2_????.????_data_Run????????_Subrun00000000_????????.i3.zst")))

def find_correct_file(run_files, eventnum):
    # open the last run file and find the first event ID
    event_id_last_file = find_first_event_id(run_files[-1])
    print("Last run file starts at ID {}, looking for {}".format(event_id_last_file, eventnum))

    if eventnum >= event_id_last_file:
        print("Event ID must be in the last file {}".format(run_files[-1]))
        return run_files[-1]


    # guess the correct file
    file_index = int(float(eventnum)/float(event_id_last_file)*float(len(run_files)))
    print("Searching, first guess file index is {}, number of files is {}.".format(file_index, len(run_files)))

    while True:
        print("Trying file {}.".format(run_files[file_index]))
        first_event_id_current = find_first_event_id(run_files[file_index])
        if first_event_id_current > eventnum:
            print("File {} starts with event ID {} which is beyond what we are looking for ({}).".format(run_files[file_index], first_event_id_current, eventnum))
            if file_index > 0:
                file_index -= 1
                continue
            else:
                print("Event seems to happen before the first event in the run (ID {}). Cannot find event ID {}.".format(first_event_id_current, eventnum))
                return None
        else: # eventnum >= first_event_id_current
            # this might be the correct file, but we need to look at the next one
            first_event_id_next = find_first_event_id(run_files[file_index+1])
            if first_event_id_next > eventnum:
                print("File {} starts with ID {}. The next file starts with event ID {}. ID {} must be in this file!".format(run_files[file_index], first_event_id_current, first_event_id_next, eventnum))
                return run_files[file_index]
            else:
                print("File {} was a candidate, but event ID {} is probably in the next file which starts at ID {}".format(run_files[file_index], eventnum, first_event_id_next))
                file_index += 1
                continue

infile = find_correct_file(run_files, eventnum)
if infile is None:
    raise RuntimeError("No valid input file found.")

_, base_infile = os.path.split(infile)
file, ext = os.path.splitext(base_infile)

if ext in ['.zst', '.gz']:
    file, ext2 = os.path.splitext(file)
    ext = ext2+ext

outfile_fixed_dec = file+'_event{}'.format(eventnum)+ext

print("Reading GCD from {}".format(GCD_file))
print("Reading from {}".format(infile))
print("Writing to {}".format(outfile_fixed_dec))

tray = I3Tray()

tray.Add("I3Reader", "reader", FilenameList=[GCD_file, infile])

def keep_QP_event_num(frame, event_num, p_frame_splits=['InIceSplit'], sub_event_id=None):
    header = frame['I3EventHeader']
    if header.event_id != event_num:
        return False
    
    if frame.Stop != icetray.I3Frame.Physics:
        keep_QP_event_num.event_encountered = True
        return True
    
    # for P-frames check the "split"
    if header.sub_event_stream not in p_frame_splits:
        return False

    if sub_event_id is not None:
        if header.sub_event_id != sub_event_id:
            return False
    
    keep_QP_event_num.event_encountered = True
    return True
keep_QP_event_num.event_encountered = False
tray.Add(keep_QP_event_num, "keep_QP_event_num",
    Streams=[icetray.I3Frame.DAQ, icetray.I3Frame.Physics],
    event_num=eventnum,
    sub_event_id=0,
    )

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


if not keep_QP_event_num.event_encountered:
    raise RuntimeError("Never found event ID {}.".format(eventnum))
