"""Tools for loading the scan state."""

# fmt: off
# mypy: ignore-errors
# pylint: skip-file

import os
from typing import List

from icecube import dataio, icetray

from .. import config as cfg
from . import LOGGER
from .event_tools import EventMetadata
from .pixelreco import PixelReco
from .utils import hash_frame_packet, load_GCD_frame_packet_from_file


def load_cache_state(
    event_metadata: EventMetadata,
    reco_algo: str,
    filestager=None,
    cache_dir: str = "./cache/",
) -> dict:
    this_event_cache_dir = os.path.join(cache_dir, str(event_metadata))
    if not os.path.isdir(this_event_cache_dir):
        raise NotADirectoryError("event \"{0}\" not found in cache at \"{1}\".".format(str(event_metadata), this_event_cache_dir))

    # load GCDQp state first
    state_dict = load_GCDQp_state(event_metadata, filestager=filestager, cache_dir=cache_dir)

    # update with scans
    state_dict = load_scan_state(event_metadata, state_dict, reco_algo, filestager=filestager, cache_dir=cache_dir)[1]

    return state_dict


"""
Code extracted from load_scan_state()
"""    
def get_baseline_gcd_frames(baseline_GCD_file, GCDQp_packet, filestager) -> List[icetray.I3Frame]:

    if baseline_GCD_file is not None:
          
        LOGGER.debug("trying to read GCD from {0}".format(baseline_GCD_file))
        try:
            baseline_GCD_frames = load_GCD_frame_packet_from_file(baseline_GCD_file, filestager=filestager)
        except:
            baseline_GCD_frames = None
            LOGGER.debug(" -> failed")
        if baseline_GCD_frames is not None:
            LOGGER.debug(" -> success")

        if baseline_GCD_frames is None:
            for GCD_base_dir in cfg.GCD_BASE_DIRS:
                read_url = os.path.join(GCD_base_dir, baseline_GCD_file)
                LOGGER.debug("trying to read GCD from {0}".format(read_url))
                try:
                    baseline_GCD_frames = load_GCD_frame_packet_from_file(read_url, filestager=filestager)                
                except:
                    LOGGER.debug(" -> failed")
                    baseline_GCD_frames=None

                if baseline_GCD_frames is not None:
                    LOGGER.debug(" -> success")
                    break

            if baseline_GCD_frames is None:
                raise RuntimeError("Could not load basline GCD file from any location")
    else:
        # assume we have full non-diff GCD frames in the packet
        baseline_GCD_frames = [GCDQp_packet[0]]
        if "I3Geometry" not in baseline_GCD_frames[0]:
            raise RuntimeError("No baseline GCD file available but main packet G frame does not contain I3Geometry")
    return baseline_GCD_frames


def load_scan_state(
    event_metadata: EventMetadata,
    state_dict: dict,
    reco_algo: str,
    filestager=None,
    cache_dir: str = "./cache/"
) -> dict:
    
    geometry = get_baseline_gcd_frames(
        state_dict.get(cfg.STATEDICT_BASELINE_GCD_FILE),
        state_dict.get(cfg.STATEDICT_GCDQP_PACKET),
        filestager,
    )[0]

    this_event_cache_dir = os.path.join(cache_dir, str(event_metadata))
    if not os.path.isdir(this_event_cache_dir):
        raise NotADirectoryError("event \"{0}\" not found in cache at \"{1}\".".format(str(event_metadata), this_event_cache_dir))

    # get all directories
    nsides = [(int(d[5:]), os.path.join(this_event_cache_dir, d)) for d in os.listdir(this_event_cache_dir) if os.path.isdir(os.path.join(this_event_cache_dir, d)) and d.startswith("nside")]

    if cfg.STATEDICT_NSIDES not in state_dict:
        state_dict[cfg.STATEDICT_NSIDES] = dict()

    for nside, nside_dir in nsides:
        if nside not in state_dict[cfg.STATEDICT_NSIDES]:
            state_dict[cfg.STATEDICT_NSIDES][nside] = dict()

        pixels = [(int(d[3:-3]), os.path.join(nside_dir, d)) for d in os.listdir(nside_dir) if os.path.isfile(os.path.join(nside_dir, d)) and d.startswith("pix") and d.endswith(".i3")]

        for pixel, pixel_file in pixels:
            loaded_frames = load_GCD_frame_packet_from_file(pixel_file)
            if len(loaded_frames) == 0:
                continue  # skip empty files
            if len(loaded_frames) > 1:
                raise RuntimeError("Pixel file \"{0}\" has more than one frame in it.")

            # add PixelReco to pixel-dict
            state_dict[cfg.STATEDICT_NSIDES][nside][pixel] = PixelReco.from_i3frame(
                loaded_frames[0], geometry, reco_algo
            )

        # get rid of empty dicts
        if len(state_dict[cfg.STATEDICT_NSIDES][nside]) == 0:
            del state_dict[cfg.STATEDICT_NSIDES][nside]

    return state_dict


def load_GCDQp_state(event_metadata: EventMetadata, filestager=None, cache_dir="./cache/") -> dict:
    this_event_cache_dir = os.path.join(cache_dir, str(event_metadata))
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
        raise RuntimeError("event \"{0}\" not found in cache at \"{1}\".".format(str(event_metadata), GCDQp_filename))

    frame_packet = load_GCD_frame_packet_from_file(GCDQp_filename)
    LOGGER.debug("loaded frame packet from {0}".format(GCDQp_filename))

    if os.path.isfile(potential_GCD_diff_base_filename):
        if potential_original_GCD_diff_base_filename is None:
            # load and throw away to make sure it is readable
            load_GCD_frame_packet_from_file(potential_GCD_diff_base_filename)
            LOGGER.debug(" - has a frame diff packet at {0}".format(potential_GCD_diff_base_filename))
            GCD_diff_base_filename = potential_GCD_diff_base_filename
            
            raise RuntimeError("Cache state seems to require a GCD diff baseline file (it contains a cached version), but the cache does not have \"original_base_GCD_for_diff_filename.txt\". This is a bug or corrupted data.")
        else:
            if filestager is None:
                orig_packet = None
                for GCD_base_dir in cfg.GCD_BASE_DIRS:
                    try:
                        read_path = os.path.join(GCD_base_dir, potential_original_GCD_diff_base_filename)
                        LOGGER.debug("reading GCD from {0}".format(read_path))
                        orig_packet = load_GCD_frame_packet_from_file(read_path)
                    except:
                        LOGGER.debug(" -> failed")
                        orig_packet = None
                    if orig_packet is None:
                        raise RuntimeError("Could not read the input GCD file \"{0}\" from any pre-configured location".format(potential_original_GCD_diff_base_filename))
            else:
                # try to load the base file from the various possible input directories
                GCD_diff_base_handle = None
                for GCD_base_dir in cfg.GCD_BASE_DIRS:
                    try:
                        read_url = os.path.join(GCD_base_dir, potential_original_GCD_diff_base_filename)
                        LOGGER.debug("reading GCD from {0}".format( read_url ))
                        GCD_diff_base_handle = filestager.GetReadablePath( read_url )
                        if not os.path.isfile( str(GCD_diff_base_handle) ):
                            raise RuntimeError("file does not exist (or is not a file)")
                    except:
                        LOGGER.debug(" -> failed")
                        GCD_diff_base_handle=None
                    if GCD_diff_base_handle is not None:
                        LOGGER.debug(" -> success")
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
            
            LOGGER.debug(" - has a frame diff packet at {0} (using original copy)".format(os.path.join(GCD_base_dir, potential_original_GCD_diff_base_filename)))
            GCD_diff_base_filename = potential_original_GCD_diff_base_filename
    else:
        LOGGER.debug(" - does not seem to contain frame diff packet")
        GCD_diff_base_filename = None

    return {
        cfg.STATEDICT_GCDQP_PACKET: frame_packet,
        cfg.STATEDICT_BASELINE_GCD_FILE: GCD_diff_base_filename,
    }


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
    packets = load_cache_state(
        eventID,
        args.reco_algo,  # TODO: add --reco-algo (see start_scan.py)
        filestager=stagers,
        cache_dir=options.CACHEDIR
    )

    print(("got:", packets))
