import os
import shutil
import json
import hashlib

from icecube import icetray, dataclasses, dataio
from icecube import full_event_followup, frame_object_diff

import config
from utils import create_event_id, load_GCD_frame_packet_from_file, save_GCD_frame_packet_to_file, hash_frame_packet, rewrite_frame_stop
from load_scan_state import load_scan_state
from prepare_frames import prepare_frames

def extract_GCD_diff_base_filename(frame_packet):
    # check the base filename (it should be the same for all "Diff" objects)
    GCD_diff_base_filename = None
    for frame in frame_packet:
        # only check GCD frames
        if frame.Stop not in [icetray.I3Frame.Geometry, icetray.I3Frame.Calibration, icetray.I3Frame.DetectorStatus]: continue

        for key in frame.keys():
            if frame.get_stop(key) != frame.Stop: continue # only look at native stops
            if not key.endswith('Diff'): continue # skip non-diff keys
            base_filename = frame[key].base_filename

            if GCD_diff_base_filename is None:
                GCD_diff_base_filename = frame[key].base_filename
            elif frame[key].base_filename != GCD_diff_base_filename:
                raise RuntimeError("inconsistent frame diff base GCD file names. expected {0}, got {1}".format(GCD_diff_base_filename, frame[key].base_filename))
    
    if GCD_diff_base_filename == "current-gcd":
        print " **** WARNING: baseline GCD file is \"current-gcd\". replacing with \"2016_01_08_Run127381.i3\"."
        GCD_diff_base_filename = "2016_01_08_Run127381.i3"
    
    return GCD_diff_base_filename

def extract_json_message(json_data, filestager, cache_dir="./cache/", override_GCD_filename=None):
    if not os.path.exists(cache_dir):
        raise RuntimeError("cache directory \"{0}\" does not exist.".format(cache_dir))
    if not os.path.isdir(cache_dir):
        raise RuntimeError("cache directory \"{0}\" is not a directory.".format(cache_dir))

    # extract the packet
    frame_packet = full_event_followup.i3live_json_to_frame_packet(json.dumps(json_data), pnf_framing=True)

    r = __extract_frame_packet(frame_packet, filestager=filestager, cache_dir=cache_dir, override_GCD_filename=override_GCD_filename)
    event_id = r[1]
    state_dict = r[2]

    # try to load existing pixels if there are any
    return load_scan_state(event_id, state_dict, cache_dir=cache_dir)

def __extract_frame_packet(frame_packet, filestager, cache_dir="./cache/", override_GCD_filename=None):
    if not os.path.exists(cache_dir):
        raise RuntimeError("cache directory \"{0}\" does not exist.".format(cache_dir))
    if not os.path.isdir(cache_dir):
        raise RuntimeError("cache directory \"{0}\" is not a directory.".format(cache_dir))

    # sanity check the packet
    if len(frame_packet) != 5:
        raise RuntimeError("frame packet length is not 5")
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
    print "event ID is {0}".format(event_id_string)

    # create the cache directory if necessary
    this_event_cache_dir = os.path.join(cache_dir, event_id_string)
    if os.path.exists(this_event_cache_dir) and not os.path.isdir(this_event_cache_dir):
        raise RuntimeError("this event would be cached in directory \"{0}\", but it exists and is not a directory".format(this_event_cache_dir))
    if not os.path.exists(this_event_cache_dir):
        os.mkdir(this_event_cache_dir)

    # see if we have the required baseline GCD to which to apply the GCD diff
    GCD_diff_base_filename = extract_GCD_diff_base_filename(frame_packet)
    if GCD_diff_base_filename is not None:
        if override_GCD_filename is not None and GCD_diff_base_filename != override_GCD_filename:
            print "** WARNING: user chose to override the GCD base filename. Message references \"{0}\", user chose \"{1}\".".format(GCD_diff_base_filename, override_GCD_filename)
            GCD_diff_base_filename = override_GCD_filename

        # seems to be a GCD diff
        print "packet needs GCD diff based on file \"{0}\"".format(GCD_diff_base_filename)

        # try to load the base file from the various possible input directories
        GCD_diff_base_handle = None
        for GCD_base_dir in config.GCD_base_dirs:
            try:
                read_url = os.path.join(GCD_base_dir, GCD_diff_base_filename)
                print "reading GCD from {0}".format( read_url )
                GCD_diff_base_handle = filestager.GetReadablePath( read_url )
                if not os.path.isfile( str(GCD_diff_base_handle) ):
                    raise RuntimeError("file does not exist (or is not a file)")
            except:
                print " -> failed"
                GCD_diff_base_handle=None
            if GCD_diff_base_handle is not None:
                print " -> success"
                break
        
        if GCD_diff_base_handle is None:
            raise RuntimeError("Could not read the input GCD file \"{0}\" from any pre-configured location".format(GCD_diff_base_filename))
            
        new_GCD_base_filename = os.path.join(this_event_cache_dir, "base_GCD_for_diff.i3")

        diff_referenced = load_GCD_frame_packet_from_file( str(GCD_diff_base_handle) )
        if os.path.exists(new_GCD_base_filename):
            diff_in_cache = load_GCD_frame_packet_from_file(new_GCD_base_filename)
            diff_in_cache_hash = hash_frame_packet(diff_in_cache)
            diff_referenced_hash = hash_frame_packet(diff_referenced)
            if diff_in_cache_hash != diff_referenced_hash:
                # print "existing:", existing_packet_hash
                # print "this_frame:", this_packet_hash
                raise RuntimeError("existing baseline GCD in cache (SHA1 {0}) and packet from input (SHA1 {1}) differ.".format(diff_in_cache_hash, diff_referenced_hash))
                print "checked baseline GCD against existing data in cache - consistent"
        else:
            save_GCD_frame_packet_to_file(diff_referenced, new_GCD_base_filename)
            print "wrote baseline GCD frames to {0}".format(new_GCD_base_filename)

        # save the GCD filename
        original_GCD_diff_base_filename = os.path.join(this_event_cache_dir, "original_base_GCD_for_diff_filename.txt")
        if os.path.isfile(original_GCD_diff_base_filename):
            f = open(original_GCD_diff_base_filename, 'r')
            filename = f.read()
            del f
            if filename != GCD_diff_base_filename:
                raise RuntimeError("expected the stored GCD base filename to be {0}. It is {1}.".format(GCD_diff_base_filename, filename))
        with open(original_GCD_diff_base_filename, "w") as text_file:
            text_file.write(GCD_diff_base_filename)
    else:
        print "packet does not need a GCD diff"

    if GCD_diff_base_filename is not None:
        frame_packet, ExcludedDOMs = prepare_frames(frame_packet, str(GCD_diff_base_handle))
    else:
        frame_packet, ExcludedDOMs = prepare_frames(frame_packet, None)

    print "ExcludedDOMs is", ExcludedDOMs

    # move the last packet frame from Physics to the 'p' stream
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('p'))

    GCDQp_filename = os.path.join(this_event_cache_dir, "GCDQp.i3")
    if os.path.exists(GCDQp_filename):
        # GCD already exists - check to make sure it is consistent
        this_packet_hash = hash_frame_packet(frame_packet)
        existing_packet = load_GCD_frame_packet_from_file(GCDQp_filename)
        existing_packet_hash = hash_frame_packet(existing_packet)
        if this_packet_hash != existing_packet_hash:
            # print "existing:", existing_packet_hash
            # print "this_frame:", this_packet_hash
            raise RuntimeError("existing GCDQp packet in cache (SHA1 {0}) and packet from input (SHA1 {1}) differ.".format(existing_packet_hash, this_packet_hash))
        print "checked dependency against existing data in cache - consistent"
    else:
        # no GCD exists yet
        save_GCD_frame_packet_to_file(frame_packet, GCDQp_filename)
        print "wrote GCDQp dependency frames to {0}".format(GCDQp_filename)

    return (this_event_cache_dir, event_id_string, dict(GCDQp_packet=frame_packet, baseline_GCD_file=GCD_diff_base_filename))


def extract_json_messages(filenames, filestager, cache_dir="./cache", override_GCD_filename=None):
    all_messages = []
    return_packets = dict()

    for filename in filenames:
        with open(filename) as json_file:
            json_data = json.load(json_file)

        if isinstance(json_data, list):
            # interpret as a list of messages
            for m in json_data:
                name, packet = extract_json_message(m, filestager=filestager, cache_dir=cache_dir, override_GCD_filename=override_GCD_filename)
                return_packets[name] = packet
        elif isinstance(json_data, dict):
            # interpret as a single message
            name, packet = extract_json_message(json_data, filestager=filestager, cache_dir=cache_dir, override_GCD_filename=override_GCD_filename)
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
    parser.add_option("-g", "--override-GCD-filename", action="store", type="string",
        default=None, dest="OVERRIDEGCDFILENAME", help="Use this GCD baseline file instead of the one referenced by the message")

    # get parsed args
    (options,args) = parser.parse_args()

    filenames = args

    if len(filenames) == 0:
        raise RuntimeError("need to specify at least one input filename")

    # get the file stager instance
    stagers = dataio.get_stagers()

    # do the work
    packets = extract_json_messages(filenames, filestager=stagers, cache_dir=options.CACHEDIR, override_GCD_filename=options.OVERRIDEGCDFILENAME)

    print "got:", packets
