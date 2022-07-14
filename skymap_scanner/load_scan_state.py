"""Tools for loading the scan state."""

# fmt: off
# mypy: ignore-errors
# pylint: skip-file

import os
from typing import Tuple

import numpy
from I3Tray import I3Units
from icecube import VHESelfVeto, dataclasses, dataio

from . import config
from .utils import StateDict, hash_frame_packet, load_GCD_frame_packet_from_file


def load_cache_state(
    event_id: str,
    filestager=None,
    cache_dir: str = "./cache/",
) -> Tuple[str, StateDict]:
    this_event_cache_dir = os.path.join(cache_dir, event_id)
    if not os.path.isdir(this_event_cache_dir):
        raise NotADirectoryError("event \"{0}\" not found in cache at \"{1}\".".format(event_id, this_event_cache_dir))

    # load GCDQp state first
    state_dict = load_GCDQp_state(event_id, filestager=filestager, cache_dir=cache_dir)[1]

    # update with scans
    state_dict = load_scan_state(event_id, state_dict, filestager=filestager, cache_dir=cache_dir)[1]

    return (event_id, state_dict)


def get_reco_losses_inside(p_frame, g_frame):
    if "MillipedeStarting2ndPass" not in p_frame: return numpy.nan, numpy.nan
    recoParticle = p_frame["MillipedeStarting2ndPass"]

    if "MillipedeStarting2ndPassParams" not in p_frame: return numpy.nan, numpy.nan
    
    def getRecoLosses(vecParticles):
        losses = []
        for p in vecParticles:
            if not p.is_cascade: continue
            if p.energy==0.: continue
            losses.append([p.time, p.energy])
        return losses
    recoLosses = getRecoLosses(p_frame["MillipedeStarting2ndPassParams"])

    intersectionPoints = VHESelfVeto.IntersectionsWithInstrumentedVolume(g_frame["I3Geometry"], recoParticle)
    intersectionTimes = []
    for intersectionPoint in intersectionPoints:
        vecX = intersectionPoint.x - recoParticle.pos.x
        vecY = intersectionPoint.y - recoParticle.pos.y
        vecZ = intersectionPoint.z - recoParticle.pos.z
        
        prod = vecX*recoParticle.dir.x + vecY*recoParticle.dir.y + vecZ*recoParticle.dir.z
        dist = numpy.sqrt(vecX**2 + vecY**2 + vecZ**2)
        if prod < 0.: dist *= -1.
        intersectionTimes.append(dist/dataclasses.I3Constants.c + recoParticle.time)

    entryTime = None
    exitTime = None
    intersectionTimes = sorted(intersectionTimes)
    if len(intersectionTimes)==0:
        return 0., 0.
        
    entryTime = intersectionTimes[0]-60.*I3Units.m/dataclasses.I3Constants.c
    intersectionTimes = intersectionTimes[1:]
    exitTime = intersectionTimes[-1]+60.*I3Units.m/dataclasses.I3Constants.c
    intersectionTimes = intersectionTimes[:-1]

    totalRecoLosses = 0.
    totalRecoLossesInside = 0.
    for entry in recoLosses:
        totalRecoLosses += entry[1]
        if entryTime is not None and entry[0] < entryTime: continue
        if exitTime  is not None and entry[0] > exitTime:  continue
        totalRecoLossesInside += entry[1]

    return totalRecoLossesInside, totalRecoLosses


"""
Code extracted from load_scan_state()
"""    
def get_baseline_gcd_frames(baseline_GCD_file, GCDQp_packet, filestager):

    if baseline_GCD_file is not None:
          
        print("trying to read GCD from {0}".format(baseline_GCD_file))
        try:
            baseline_GCD_frames = load_GCD_frame_packet_from_file(baseline_GCD_file, filestager=filestager)
        except:
            baseline_GCD_frames = None
            print(" -> failed")
        if baseline_GCD_frames is not None:
            print(" -> success")

        if baseline_GCD_frames is None:
            for GCD_base_dir in config.GCD_BASE_DIRS:
                read_url = os.path.join(GCD_base_dir, baseline_GCD_file)
                print(("trying to read GCD from {0}".format( read_url )))
                try:
                    baseline_GCD_frames = load_GCD_frame_packet_from_file(read_url, filestager=filestager)                
                except:
                    print(" -> failed")
                    baseline_GCD_frames=None

                if baseline_GCD_frames is not None:
                    print(" -> success")
                    break

            if baseline_GCD_frames is None:
                 raise RuntimeError("Could not load basline GCD file from any location")
    else:
        # assume we have full non-diff GCD frames in the packet
        baseline_GCD_frames = [GCDQp_packet[0]]
        if "I3Geometry" not in baseline_GCD_frames[0]:
            raise RuntimeError("No baseline GCD file available but main packet G frame does not contain I3Geometry")
    return baseline_GCD_frames


def load_scan_state(event_id, state_dict, filestager=None, cache_dir="./cache/"):
    
    baseline_GCD_frames = get_baseline_gcd_frames(
        state_dict.get("baseline_GCD_file"),
        state_dict.get("GCDQp_packet"),
        filestager,
    )

    this_event_cache_dir = os.path.join(cache_dir, event_id)
    if not os.path.isdir(this_event_cache_dir):
        raise NotADirectoryError("event \"{0}\" not found in cache at \"{1}\".".format(event_id, this_event_cache_dir))

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

            recoLossesInside, recoLossesTotal = get_reco_losses_inside(loaded_frames[0], baseline_GCD_frames[0])

            state_dict["nsides"][nside][pixel] = dict(frame=loaded_frames[0], llh=llh, recoLossesInside=recoLossesInside, recoLossesTotal=recoLossesTotal)

        # get rid of empty dicts
        if len(state_dict["nsides"][nside]) == 0:
            del state_dict["nsides"][nside]

    return (event_id, state_dict)


def load_GCDQp_state(event_id, filestager=None, cache_dir="./cache/"):
    this_event_cache_dir = os.path.join(cache_dir, event_id)
    GCDQp_filename = os.path.join(this_event_cache_dir, "GCDQp.i3")
    potential_GCD_diff_base_filename = os.path.join(this_event_cache_dir, "base_GCD_for_diff.i3")

    potential_original_GCD_diff_base_filename = os.path.join(this_event_cache_dir, "original_base_GCD_for_diff_filename.txt")
    if os.path.isfile(potential_original_GCD_diff_base_filename):
        f = open(potential_original_GCD_diff_base_filename, 'r')
        potential_original_GCD_diff_base_filename = f.read()
        del f
    else:
        potential_original_GCD_diff_base_filename = None

    if not os.path.isfile(GCDQp_filename):
        raise RuntimeError("event \"{0}\" not found in cache at \"{1}\".".format(event_id, GCDQp_filename))

    frame_packet = load_GCD_frame_packet_from_file(GCDQp_filename)
    print(("loaded frame packet from {0}".format(GCDQp_filename)))

    if os.path.isfile(potential_GCD_diff_base_filename):
        if potential_original_GCD_diff_base_filename is None:
            # load and throw away to make sure it is readable
            load_GCD_frame_packet_from_file(potential_GCD_diff_base_filename)
            print((" - has a frame diff packet at {0}".format(potential_GCD_diff_base_filename)))
            GCD_diff_base_filename = potential_GCD_diff_base_filename
            
            raise RuntimeError("Cache state seems to require a GCD diff baseline file (it contains a cached version), but the cache does not have \"original_base_GCD_for_diff_filename.txt\". This is a bug or corrupted data.")
        else:
            if filestager is None:
                orig_packet = None
                for GCD_base_dir in config.GCD_BASE_DIRS:
                    try:
                        read_path = os.path.join(GCD_base_dir, potential_original_GCD_diff_base_filename)
                        print(("reading GCD from {0}".format( read_url )))
                        orig_packet = load_GCD_frame_packet_from_file(read_path)
                    except:
                        print(" -> failed")
                        orig_packet = None
                    if orig_packet is None:
                        raise RuntimeError("Could not read the input GCD file \"{0}\" from any pre-configured location".format(potential_original_GCD_diff_base_filename))
            else:
                # try to load the base file from the various possible input directories
                GCD_diff_base_handle = None
                for GCD_base_dir in config.GCD_BASE_DIRS:
                    try:
                        read_url = os.path.join(GCD_base_dir, potential_original_GCD_diff_base_filename)
                        print(("reading GCD from {0}".format( read_url )))
                        GCD_diff_base_handle = filestager.GetReadablePath( read_url )
                        if not os.path.isfile( str(GCD_diff_base_handle) ):
                            raise RuntimeError("file does not exist (or is not a file)")
                    except:
                        print(" -> failed")
                        GCD_diff_base_handle=None
                    if GCD_diff_base_handle is not None:
                        print(" -> success")
                        break
                
                if GCD_diff_base_handle is None:
                    raise RuntimeError("Could not read the input GCD file \"{0}\" from any pre-configured location".format(potential_original_GCD_diff_base_filename))

                orig_packet = load_GCD_frame_packet_from_file( str(GCD_diff_base_handle) )
            this_packet = load_GCD_frame_packet_from_file(potential_GCD_diff_base_filename)
            
            orig_packet_hash = hash_frame_packet(orig_packet)
            this_packet_hash = hash_frame_packet(this_packet)
            if orig_packet_hash != this_packet_hash:
                raise RuntimeError("cached GCD baseline file is different from the original file")

            del orig_packet
            del this_packet
            
            print((" - has a frame diff packet at {0} (using original copy)".format(os.path.join(GCD_base_dir, potential_original_GCD_diff_base_filename))))
            GCD_diff_base_filename = potential_original_GCD_diff_base_filename
    else:
        print(" - does not seem to contain frame diff packet")
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

    # get the file stager instance
    stagers = dataio.get_stagers()

    # do the work
    packets = load_cache_state(eventID, filestager=stagers, cache_dir=options.CACHEDIR)

    print(("got:", packets))
