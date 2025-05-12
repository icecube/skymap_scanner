"""Tools for loading the scan state."""

# fmt: off
# pylint: skip-file

import logging
import os
from typing import List

from icecube import icetray  # type: ignore[import-not-found]
from skyreader import EventMetadata

from .. import config as cfg
from .pixel_classes import RecoPixelFinal, RecoPixelVariation
from .utils import hash_frame_packet, load_framepacket_from_file

LOGGER = logging.getLogger(__name__)


def load_cache_state(
    event_metadata: EventMetadata,
    reco_algo: str,
    cache_dir: str = "./cache/",
) -> dict:
    this_event_cache_dir = os.path.join(cache_dir, str(event_metadata))
    if not os.path.isdir(this_event_cache_dir):
        raise NotADirectoryError(f"event \"{str(event_metadata)}\" not found in cache at \"{this_event_cache_dir}\".")

    # load GCDQp state first
    LOGGER.debug("Initialize state_dict with GCDQp")
    state_dict = load_GCDQp_state(event_metadata, cache_dir=cache_dir)

    # update with scans
    LOGGER.debug("Update state_dict with scan state.")
    state_dict = load_scan_state(event_metadata, state_dict, reco_algo, cache_dir=cache_dir)[1]

    return state_dict


"""
Code extracted from load_scan_state()
"""
def get_baseline_gcd_frames(baseline_GCD_file, GCDQp_packet) -> List[icetray.I3Frame]:

    if baseline_GCD_file is not None:

        LOGGER.debug(f"Trying to read GCD from {baseline_GCD_file}.")
        try:
            baseline_GCD_frames = load_framepacket_from_file(baseline_GCD_file)
        except Exception:
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
    cache_dir: str = "./cache/"
) -> dict:

    geometry = get_baseline_gcd_frames(
        state_dict.get(cfg.STATEDICT_BASELINE_GCD_FILE),
        state_dict.get(cfg.STATEDICT_GCDQP_PACKET),
    )[0]

    this_event_cache_dir = os.path.join(cache_dir, str(event_metadata))
    if not os.path.isdir(this_event_cache_dir):
        raise NotADirectoryError(f"event \"{str(event_metadata)}\" not found in cache at \"{this_event_cache_dir}\".")

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

            # add RecoPixelFinal to pixel-dict
            state_dict[cfg.STATEDICT_NSIDES][nside][pixel] = RecoPixelFinal.from_recopixelvariation(
                RecoPixelVariation.from_i3frame(
                    loaded_frames[0], geometry, reco_algo
                )
            )

        # get rid of empty dicts
        if len(state_dict[cfg.STATEDICT_NSIDES][nside]) == 0:
            del state_dict[cfg.STATEDICT_NSIDES][nside]

    return state_dict


def load_GCDQp_state(event_metadata: EventMetadata, cache_dir="./cache/") -> dict:
    """Load GCDQp from a cache directory.

    This function may be used for reading a cache from the legacy skymap
    scanners.
    """
    event_cache_dir = os.path.join(cache_dir, str(event_metadata))

    # GCDQp previously cached by extract_json_message()
    GCDQp_filename = os.path.join(event_cache_dir, cfg.GCDQp_FILENAME)
    if not os.path.isfile(GCDQp_filename):
        raise RuntimeError(f"GCQDp file for event \"{str(event_metadata)}\" not found in cache at \"{GCDQp_filename}\".")
    frame_packet = load_framepacket_from_file(GCDQp_filename)
    LOGGER.debug(f"Loaded frame packet from {GCDQp_filename}")

    # cached baseline GCD
    cached_baseline_GCD = os.path.join(event_cache_dir, cfg.BASELINE_GCD_FILENAME)
    # source path of cached baseline GCD is stored in metadata file
    source_baseline_GCD_metadata = os.path.join(event_cache_dir, cfg.SOURCE_BASELINE_GCD_METADATA)

    if os.path.isfile(source_baseline_GCD_metadata):
        with open(source_baseline_GCD_metadata, 'r') as f:
            source_baseline_GCD = f.read()
    else:
        source_baseline_GCD = None

    if os.path.isfile(cached_baseline_GCD):
        if source_baseline_GCD is None:
            # load and throw away to make sure it is readable
            load_framepacket_from_file(cached_baseline_GCD)
            LOGGER.debug(f" - has a frame diff packet ref. to cached baseline {cached_baseline_GCD}")
            raise RuntimeError(f"Cache state seems to require a baseline GCD file (it contains a cached version), but the cache does cointain \"{cfg.SOURCE_BASELINE_GCD_METADATA}\". This is a bug or corrupted data.")
        else:
            # For the time being, the code will try to find the corresponding GCD in cfg.DEFAULT_GCD_DIR.
            # It may be possible to access directly the path stored in source_baseline_GCD, but we ignore this possibility out of simplicity.
            # If the cache has been produced by the v3 scanner then we end up re-building the same path.
            # Maybe this will be further simplified in the future.
            source_baseline_GCD_basename = os.path.basename(source_baseline_GCD)
            source_baseline_GCD_framepacket = None
            try:
                read_path = os.path.join(cfg.DEFAULT_GCD_DIR, source_baseline_GCD_basename)
                LOGGER.debug(f"load_GCDQp_state => reading source baseline GCD from {read_path}")
                source_baseline_GCD_framepacket = load_framepacket_from_file(read_path)
            except Exception:
                LOGGER.debug(" -> failed")
                source_baseline_GCD_framepacket = None
            if source_baseline_GCD_framepacket is None:
                raise RuntimeError(f"load_GCDQp_state => Could not read the source GCD file \"{source_baseline_GCD_metadata}\"")

            cached_baseline_GCD_framepacket = load_framepacket_from_file(cached_baseline_GCD)

            source_baseline_GCD_framepacket_hash = hash_frame_packet(source_baseline_GCD_framepacket)
            cached_baseline_GCD_framepacket_hash = hash_frame_packet(cached_baseline_GCD_framepacket)
            if source_baseline_GCD_framepacket_hash != cached_baseline_GCD_framepacket_hash:
                raise RuntimeError("load_GCDQp_state => cached GCD baseline file is different from the original file")

            del source_baseline_GCD_framepacket
            del cached_baseline_GCD_framepacket

            LOGGER.debug(f" - has a frame diff packet at {os.path.join(cfg.DEFAULT_GCD_DIR, source_baseline_GCD_metadata)} (using original copy)")
    else:
        LOGGER.debug(" - does not seem to contain frame diff packet")

    return {
        cfg.STATEDICT_GCDQP_PACKET: frame_packet,
        cfg.STATEDICT_BASELINE_GCD_FILE: source_baseline_GCD,
    }
