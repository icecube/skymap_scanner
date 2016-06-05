import os
import numpy

from icecube import icetray, dataclasses, dataio
from icecube import gulliver, millipede

from utils import load_GCD_frame_packet_from_file, hash_frame_packet

def load_cache_state(event_id, cache_dir="./cache/"):
    this_event_cache_dir = os.path.join(cache_dir, event_id)
    if not os.path.isdir(this_event_cache_dir):
        raise RuntimeError("event \"{0}\" not found in cache at \"{1}\".".format(event_id, this_event_cache_dir))

    # load GCDQp state first
    state_dict = load_GCDQp_state(event_id, cache_dir=cache_dir)[1]

    # update with scans
    state_dict = load_scan_state(event_id, state_dict, cache_dir=cache_dir)[1]

    return (event_id, state_dict)


def load_scan_state(event_id, state_dict, cache_dir="./cache/"):
    this_event_cache_dir = os.path.join(cache_dir, event_id)
    if not os.path.isdir(this_event_cache_dir):
        raise RuntimeError("event \"{0}\" not found in cache at \"{1}\".".format(event_id, this_event_cache_dir))

    # get all directories
    nsides = [(int(d[5:]), os.path.join(this_event_cache_dir, d)) for d in os.listdir(this_event_cache_dir) if os.path.isdir(os.path.join(this_event_cache_dir, d)) and d.startswith("nside")]

    if "nsides" not in state_dict: state_dict["nsides"] = dict()
    for nside, nside_dir in nsides:
        if nside not in state_dict["nsides"]: state_dict["nsides"][nside] = dict()
        pixels = [(int(d[3:-3]), os.path.join(nside_dir, d)) for d in os.listdir(nside_dir) if os.path.isfile(os.path.join(nside_dir, d)) and d.startswith("pix") and d.endswith(".i3")]

        for pixel, pixel_file in pixels:
            loaded_frames = load_GCD_frame_packet_from_file(pixel_file)
            if len(loaded_frames)==0: continue # skip empty files
            if len(loaded_frames) > 1:
                raise RuntimeError("Pixel file \"{0}\" has more than one frame in it.")
            if "MillipedeStarting2ndPass_millipedellh" in loaded_frames[0]:
                llh = loaded_frames[0]["MillipedeStarting2ndPass_millipedellh"].logl
            else:
                llh = numpy.nan
            state_dict["nsides"][nside][pixel] = dict(frame=loaded_frames[0], llh=llh)

        # get rid of empty dicts
        if len(state_dict["nsides"][nside]) == 0:
            del state_dict["nsides"][nside]

    return (event_id, state_dict)


def load_GCDQp_state(event_id, cache_dir="./cache/", use_original_GCD_baseline_file_if_available=True):
    this_event_cache_dir = os.path.join(cache_dir, event_id)
    GCDQp_filename = os.path.join(this_event_cache_dir, "GCDQp.i3")
    potential_GCD_diff_base_filename = os.path.join(this_event_cache_dir, "base_GCD_for_diff.i3")

    potential_original_GCD_diff_base_filename = os.path.join(this_event_cache_dir, "original_base_GCD_for_diff_filename.txt")
    if os.path.isfile(potential_original_GCD_diff_base_filename):
        f = open(potential_original_GCD_diff_base_filename, 'r')
        filename = f.read()
        del f
        if not os.path.isfile(filename):
            print "** WARNING: original GCD_baseline file name {0} does not exist.".format(filename)
            potential_original_GCD_diff_base_filename = None
        else:
            print "** INFO: can read original GCD diff directly from {0} instead of the local copy.".format(filename)
            potential_original_GCD_diff_base_filename = filename
    else:
        potential_original_GCD_diff_base_filename = None

    if not os.path.isfile(GCDQp_filename):
        raise RuntimeError("event \"{0}\" not found in cache at \"{1}\".".format(event_id, GCDQp_filename))

    frame_packet = load_GCD_frame_packet_from_file(GCDQp_filename)
    print "loaded frame packet from {0}".format(GCDQp_filename)

    if os.path.isfile(potential_GCD_diff_base_filename):
        if potential_original_GCD_diff_base_filename is None:
            # load and throw away to make sure it is readable
            load_GCD_frame_packet_from_file(potential_GCD_diff_base_filename)
            print " - has a frame diff packet at {0}".format(potential_GCD_diff_base_filename)
            GCD_diff_base_filename = potential_GCD_diff_base_filename
        else:
            orig_packet = load_GCD_frame_packet_from_file(potential_original_GCD_diff_base_filename)
            this_packet = load_GCD_frame_packet_from_file(potential_GCD_diff_base_filename)
            
            orig_packet_hash = hash_frame_packet(orig_packet)
            this_packet_hash = hash_frame_packet(this_packet)
            if orig_packet_hash != this_packet_hash:
                raise RuntimeError("cached GCD baseline file is different from the original file")

            del orig_packet
            del this_packet
            
            if use_original_GCD_baseline_file_if_available:
                print " - has a frame diff packet at {0} (using original copy)".format(potential_original_GCD_diff_base_filename)
                GCD_diff_base_filename = potential_original_GCD_diff_base_filename
            else:
                print " - has a frame diff packet at {0} (using cached copy)".format(potential_GCD_diff_base_filename)
                GCD_diff_base_filename = potential_GCD_diff_base_filename
    else:
        print " - does not seem to contain frame diff packet"
        GCD_diff_base_filename = None

    return (event_id, dict(GCDQp_packet=frame_packet, baseline_GCD_file=GCD_diff_base_filename))


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    packets = load_cache_state(eventID, cache_dir=options.CACHEDIR)

    print "got:", packets
