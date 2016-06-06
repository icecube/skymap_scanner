import os
import shutil
import json
import hashlib

from icecube import icetray, dataio, dataclasses

def get_event_mjd(state_dict):
    if "GCDQp_packet" not in state_dict:
        raise RuntimeError("GCDQp_packet not found in state_dict")
    frame_packet = state_dict["GCDQp_packet"]
    
    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Physics and p_frame.Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("no p-frame found at the end of the GCDQp packet")
    if "I3EventHeader" not in p_frame:
        raise RuntimeError("No I3EventHeader in p-frame")
    time = p_frame["I3EventHeader"].start_time

    return time.mod_julian_day_double

def create_event_id(run_id, event_id):
    return "run{0:08d}.evt{1:012d}.HESE".format(run_id, event_id)

def parse_event_id(event_id_string):
    parts = event_id_string.split('.')
    if len(parts) != 3:
        raise RuntimeError("event ID must have 3 parts separated by '.'")

    if not parts[0].startswith("run"):
        raise RuntimeError("event ID run part does not start with \"run\"")
    if not parts[1].startswith("evt"):
        raise RuntimeError("event ID event part does not start with \"evt\"")

    run = int(parts[0][3:])
    event = int(parts[1][3:])
    evt_type = parts[2]
    return (run, event, evt_type)

def load_GCD_frame_packet_from_file(filename):
    frame_packet = []
    i3f = dataio.I3File(filename,'r')
    while True:
        frame = i3f.pop_frame()
        if frame is None:
            return frame_packet
        frame_packet.append(frame)

def save_GCD_frame_packet_to_file(frame_packet, filename):
    i3f = dataio.I3File(filename,'w')
    for frame in frame_packet:
        i3f.push(frame)
    i3f.close()
    del i3f

def hash_frame_packet(frame_packet):
    m = hashlib.sha1()
    for frame in frame_packet:
        m.update(frame.dumps())
    return m.hexdigest()

def rewrite_frame_stop(input_frame, new_stream):
    input_frame.purge() # deletes all non-native items

    for key in input_frame.keys():
        input_frame.change_stream(key, new_stream)

    new_frame = icetray.I3Frame(new_stream)
    new_frame.merge(input_frame)
    del input_frame

    return new_frame
