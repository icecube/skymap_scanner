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
from .utils import hash_frame_packet, load_framepacket_from_file


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
          
        LOGGER.debug(f"Trying to read GCD from {baseline_GCD_file}.")
        try:
            baseline_GCD_frames = load_framepacket_from_file(baseline_GCD_file, filestager=filestager)
        except:
            LOGGER.debug(" -> failed")
            raise RuntimeError("Unable to read baseline GCD. In the current design, this is unexpected. Possibly a bug or data corruption!")
        if baseline_GCD_frames is not None:
            LOGGER.debug(" -> success")
        # NOTE: Legacy code used to scan a list of GCD_BASE_DIRS.
        #       It is now assumed that assume that the passed `baseline_GCD_file` is a valid path to a baseline GCD file.

    else:
        # Assume we have full non-diff GCD frames in the packet.
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
            loaded_frames = load_framepacket_from_file(pixel_file)
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
    event_cache_dir = os.path.join(cache_dir, str(event_metadata))

    # GCDQp previously cached by extract_json_message()
    GCDQp_filename = os.path.join(event_cache_dir, cfg.GCDQp_FILENAME)
    if not os.path.isfile(GCDQp_filename):
        raise RuntimeError(f"GCQDp file for event \"{str(event_metadata)}\" not found in cache at \"{GCDQp_filename}\".")
    frame_packet = load_framepacket_from_file(GCDQp_filename)
    LOGGER.debug(f"Loaded frame packet from {GCDQp_filename}")
    
    # cached baseline GCD
    cached_baseline_GCD = os.path.join(event_cache_dir, cfg.BASELINE_GCD_FILENAME)
    # source of cached baseline GCD
    source_baseline_GCD_metadata = os.path.join(event_cache_dir, cfg.SOURCE_BASELINE_GCD_METADATA)
    if os.path.isfile(source_baseline_GCD_metadata):
        f = open(source_baseline_GCD_metadata, 'r')
        source_baseline_GCD_metadata = f.read()
        del f
    else:
        source_baseline_GCD_metadata = None

    if os.path.isfile(cached_baseline_GCD):
        if source_baseline_GCD_metadata is None:
            # load and throw away to make sure it is readable
            load_framepacket_from_file(cached_baseline_GCD)
            LOGGER.debug(f" - has a frame diff packet ref. to baseline {cached_baseline_GCD}")            
            raise RuntimeError(f"Cache state seems to require a baseline GCD file (it contains a cached version), but the cache does not have \"{cfg.SOURCE_BASELINE_GCD_METADATA}\". This is a bug or corrupted data.")
        else:
            if filestager is None:
                orig_packet = None
                for GCD_base_dir in cfg.GCD_BASE_DIRS:
                    try:
                        read_path = os.path.join(GCD_base_dir, source_baseline_GCD_metadata)
                        LOGGER.debug("load_GCDQp_state => reading GCD from {0}".format(read_path))
                        orig_packet = load_framepacket_from_file(read_path)
                    except:
                        LOGGER.debug(" -> failed")
                        orig_packet = None
                    if orig_packet is None:
                        raise RuntimeError("load_GCDQp_state => Could not read the input GCD file \"{0}\" from any pre-configured location".format(source_baseline_GCD_metadata))
            else:
                # try to load the base file from the various possible input directories
                GCD_diff_base_handle = None
                for GCD_base_dir in cfg.GCD_BASE_DIRS:
                    try:
                        read_url = os.path.join(GCD_base_dir, source_baseline_GCD_metadata)
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
                    raise RuntimeError("Could not read the input GCD file \"{0}\" from any pre-configured location".format(source_baseline_GCD_metadata))

                orig_packet = load_framepacket_from_file( str(GCD_diff_base_handle) )
            this_packet = load_framepacket_from_file(cached_baseline_GCD)
            
            orig_packet_hash = hash_frame_packet(orig_packet)
            this_packet_hash = hash_frame_packet(this_packet)
            if orig_packet_hash != this_packet_hash:
                raise RuntimeError("cached GCD baseline file is different from the original file")

            del orig_packet
            del this_packet
            
            LOGGER.debug(" - has a frame diff packet at {0} (using original copy)".format(os.path.join(GCD_base_dir, source_baseline_GCD_metadata)))
            baseline_GCD = source_baseline_GCD_metadata
    else:
        LOGGER.debug(" - does not seem to contain frame diff packet")
        baseline_GCD = None

    return {
        cfg.STATEDICT_GCDQP_PACKET: frame_packet,
        cfg.STATEDICT_BASELINE_GCD_FILE: baseline_GCD,
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
