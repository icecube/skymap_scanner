from __future__ import print_function
from __future__ import absolute_import

import os
import shutil
import json
import hashlib

from icecube import icetray, dataclasses, dataio
from icecube import astro
from icecube import full_event_followup, frame_object_diff

from . import config
from .utils import create_event_id, load_GCD_frame_packet_from_file, save_GCD_frame_packet_to_file, hash_frame_packet, rewrite_frame_stop, extract_MC_truth
from .load_scan_state import load_scan_state
from .prepare_frames import prepare_frames

def extract_json_message(json_data, filestager, base_GCD_path, cache_dir="./cache/"):
    if not os.path.exists(cache_dir):
        raise RuntimeError("cache directory \"{0}\" does not exist.".format(cache_dir))
    if not os.path.isdir(cache_dir):
        raise RuntimeError("cache directory \"{0}\" is not a directory.".format(cache_dir))

    # extract the packet
    frame_packet = full_event_followup.i3live_json_to_frame_packet(json.dumps(json_data), pnf_framing=True)

    r = __extract_frame_packet(frame_packet, filestager=filestager, base_GCD_path=base_GCD_path, cache_dir=cache_dir)
    event_id = r[1]
    state_dict = r[2]

    # try to load existing pixels if there are any
    return load_scan_state(event_id, state_dict, cache_dir=cache_dir)

def __extract_frame_packet(frame_packet, filestager, base_GCD_path, cache_dir="./cache/", pulsesName="SplitUncleanedInIcePulses"):
    if not os.path.exists(cache_dir):
        raise RuntimeError("cache directory \"{0}\" does not exist.".format(cache_dir))
    if not os.path.isdir(cache_dir):
        raise RuntimeError("cache directory \"{0}\" is not a directory.".format(cache_dir))

    # sanity check the packet
    #if len(frame_packet) != 5:
    #    raise RuntimeError("frame packet length is not 5")
    if frame_packet[-1].Stop != icetray.I3Frame.Physics and frame_packet[-1].Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("frame packet does not end with Physics frame")

    # move the last packet frame from Physics to the Physics stream
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('P'))
    physics_frame = frame_packet[-1]

    # extract event ID
    if "I3EventHeader" not in physics_frame:
        raise RuntimeError("No I3EventHeader in Physics frame")
    header = physics_frame["I3EventHeader"]
    event_id_string = create_event_id(header.run_id, header.event_id)
    print("event ID is {0}".format(event_id_string))

    # create the cache directory if necessary
    this_event_cache_dir = os.path.join(cache_dir, event_id_string)
    if os.path.exists(this_event_cache_dir) and not os.path.isdir(this_event_cache_dir):
        raise RuntimeError("this event would be cached in directory \"{0}\", but it exists and is not a directory".format(this_event_cache_dir))
    if not os.path.exists(this_event_cache_dir):
        os.mkdir(this_event_cache_dir)

    frame_packet = prepare_frames(frame_packet, base_GCD_path=base_GCD_path, pulsesName=pulsesName)

    # move the last packet frame from Physics to the 'p' stream
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('p'))

    GCDQp_filename = os.path.join(this_event_cache_dir, "GCDQp.i3")
    if os.path.exists(GCDQp_filename):
        # GCD already exists - check to make sure it is consistent
        this_packet_hash = hash_frame_packet(frame_packet)
        existing_packet = load_GCD_frame_packet_from_file(GCDQp_filename)
        existing_packet_hash = hash_frame_packet(existing_packet)
        if this_packet_hash != existing_packet_hash:
            # print("existing:", existing_packet_hash)
            # print("this_frame:", this_packet_hash)
            raise RuntimeError("existing GCDQp packet in cache (SHA1 {0}) and packet from input (SHA1 {1}) differ.".format(existing_packet_hash, this_packet_hash))
        print("checked dependency against existing data in cache - consistent")
    else:
        # no GCD exists yet
        save_GCD_frame_packet_to_file(frame_packet, GCDQp_filename)
        print("wrote GCDQp dependency frames to {0}".format(GCDQp_filename))

    state_dict = dict(GCDQp_packet=frame_packet)

    state_dict = extract_MC_truth(state_dict)

    return (this_event_cache_dir, event_id_string, state_dict)

def extract_json_messages(filenames, filestager, base_GCD_path, cache_dir="./cache"):
    all_messages = []
    return_packets = dict()

    for filename in filenames:
        with open(filename) as json_file:
            json_data = json.load(json_file)

        if isinstance(json_data, list):
            # interpret as a list of messages
            for m in json_data:
                name, packet = extract_json_message(m, filestager=filestager, base_GCD_path=base_GCD_path, cache_dir=cache_dir)
                return_packets[name] = packet
        elif isinstance(json_data, dict):
            # interpret as a single message
            name, packet = extract_json_message(json_data, filestager=filestager, base_GCD_path=base_GCD_path, cache_dir=cache_dir)
            return_packets[name] = packet
        else:
            raise RuntimeError("Cannot interpret JSON data in {0}".format(filename))

    return return_packets



if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("-g", "--base-gcd-path", action="store", type="string",
        default="./", dest="BASEGCDPATH", help="The path where baseline GCD files are stored")

    # get parsed args
    (options,args) = parser.parse_args()

    filenames = args

    if len(filenames) == 0:
        raise RuntimeError("need to specify at least one input filename")

    # get the file stager instance
    stagers = dataio.get_stagers()

    # do the work
    packets = extract_json_messages(filenames, filestager=stagers, base_GCD_path=options.BASEGCDPATH, cache_dir=options.CACHEDIR)

    print("got:", packets)
