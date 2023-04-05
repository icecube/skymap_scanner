"""Tools for extracting json messages."""

# fmt: off
# pylint: skip-file

import json
import os
from typing import Tuple

from icecube import full_event_followup, icetray  # type: ignore[import]

from .. import config as cfg
from . import LOGGER
from .event_tools import EventMetadata
from .load_scan_state import load_scan_state
from .prepare_frames import prepare_frames
from .utils import (
    get_event_mjd,
    hash_frame_packet,
    load_framepacket_from_file,
    rewrite_frame_stop,
    save_GCD_frame_packet_to_file,
)


def extract_GCD_diff_base_filename(frame_packet):
    # check the base filename (it should be the same for all "Diff" objects)
    GCD_diff_base_filename = None
    for frame in frame_packet:
        # only check GCD frames
        if frame.Stop not in [icetray.I3Frame.Geometry, icetray.I3Frame.Calibration, icetray.I3Frame.DetectorStatus]: continue

        for key in list(frame.keys()):
            if frame.get_stop(key) != frame.Stop: continue # only look at native stops
            if not key.endswith('Diff'): continue # skip non-diff keys

            if GCD_diff_base_filename is None:
                GCD_diff_base_filename = frame[key].base_filename
                LOGGER.debug(f"GCD diff base_filename loaded from {key} in {frame.Stop} frame.")
            elif frame[key].base_filename != GCD_diff_base_filename:
                raise RuntimeError("inconsistent frame diff base GCD file names. expected {0}, got {1}".format(GCD_diff_base_filename, frame[key].base_filename))

    if GCD_diff_base_filename == "current-gcd":
        # It is unclear which legacy case is covered by this condition.
        LOGGER.warning("Baseline GCD file is \"current-gcd\". Replacing with \"2016_01_08_Run127381.i3\".")
        GCD_diff_base_filename = "2016_01_08_Run127381.i3"

    return GCD_diff_base_filename


def extract_json_message(
    json_data,
    reco_algo: str,
    is_real_event: bool,
    cache_dir : str,
    GCD_dir : str,
    pulsesName
) -> Tuple[EventMetadata, dict]:
    if not os.path.exists(cache_dir):
        raise RuntimeError("cache directory \"{0}\" does not exist.".format(cache_dir))
    if not os.path.isdir(cache_dir):
        raise RuntimeError("cache directory \"{0}\" is not a directory.".format(cache_dir))

    # extract the packet
    frame_packet = full_event_followup.i3live_json_to_frame_packet(json.dumps(json_data), pnf_framing=True)

    _, event_metadata, state_dict = __extract_frame_packet(
        frame_packet,
        reco_algo=reco_algo,
        is_real_event=is_real_event,
        cache_dir=cache_dir,
        GCD_dir=GCD_dir,
        pulsesName=pulsesName
    )

    # try to load existing pixels if there are any
    state_dict = load_scan_state(event_metadata, state_dict, reco_algo, cache_dir=cache_dir)
    return event_metadata, state_dict


def __extract_event_type(physics_frame):
    if "AlertShortFollowupMsg" in physics_frame:
        alert_keys = json.loads(physics_frame["AlertShortFollowupMsg"].value).keys()
        if "hese" in alert_keys:
            return "HESE"
        elif "ehe" in alert_keys:
            return "EHE"
        elif "neutrino" in alert_keys:
            return "neutrino"
        elif "estres" in alert_keys:
            return "ESTRES"
    elif "HESE_llhratio" in physics_frame:
        return "HESE"
    elif "Estres_p_miss" in physics_frame:
        return "ESTRES"
    elif "PoleEHEOphelia_ImpLF" in physics_frame:
        return "EHE"
    return None


def __extract_frame_packet(
    frame_packet,
    reco_algo: str,
    is_real_event: bool,
    pulsesName : str,
    cache_dir : str,
    GCD_dir : str,
) -> Tuple[str, EventMetadata, dict]:
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
        raise RuntimeError("No I3EventHeader in Physics frame.")
    header = physics_frame["I3EventHeader"]
    event_metadata = EventMetadata(
        header.run_id,
        header.event_id,
        __extract_event_type(physics_frame),
        get_event_mjd(frame_packet),
        is_real_event,
    )
    LOGGER.debug("event ID is {0}".format(event_metadata))

    # create the cache directory if necessary
    event_cache_dir = os.path.join(cache_dir, str(event_metadata))
    if os.path.exists(event_cache_dir) and not os.path.isdir(event_cache_dir):
        raise RuntimeError("This event would be cached in directory \"{0}\", but it exists and is not a directory.".format(event_cache_dir))
    if not os.path.exists(event_cache_dir):
        os.mkdir(event_cache_dir)

    # see if we have the required baseline GCD to which to apply the GCD diff
    
    baseline_GCD = extract_GCD_diff_base_filename(frame_packet)

    # Deal with different scenarios:
    # if packet has GCD diff (realtime alert):
    # - retrieve baseline GCD name from frame
    # - lookup corresponding file in GCD_dir
    # - cache baseline GCD file and medatadata (check consistency if already cached)
    # if packet does not have GCD (GFU event or legacy EHE)
    # - look up baseline GCD in GCD_dir based on run number
    # - assemble GCDQp from baseline GCD

    LOGGER.debug(f"Extracted GCD_diff_base_filename = {baseline_GCD}.")
    LOGGER.debug(f"GCD dir is set to = {GCD_dir}.")

    #=====================
    # GCD-diff framepacket
    #=====================
    if baseline_GCD is None:
        LOGGER.debug("Packet does not need a GCD diff.")
    else:
        # assume GCD dir is always valid
        baseline_GCD_file = os.path.join(GCD_dir, baseline_GCD)
        LOGGER.debug(f"Trying GCD file: {baseline_GCD_file}")
        if not os.path.isfile(baseline_GCD_file):
            raise RuntimeError("Baseline GCD file not available!")
        # NOTE: logic allowing GCD_dir to point to a file, in order to directly override the GCD has been removed.
        
        cached_baseline_GCD_file = os.path.join(event_cache_dir, cfg.BASELINE_GCD_FILENAME)

        baseline_GCD_framepacket = load_framepacket_from_file(baseline_GCD_file)

        if os.path.exists(cached_baseline_GCD_file):
            # this should occur if the cache is isolated on a server-instance basis
            # but we keep it for the time being in case we want to read back an old scan
            baseline_GCD_hash = hash_frame_packet(baseline_GCD_framepacket)

            cached_baseline_GCD_framepacket = load_framepacket_from_file(cached_baseline_GCD_file)
            cached_baseline_GCD_hash = hash_frame_packet(cached_baseline_GCD_framepacket)

            if cached_baseline_GCD_hash != baseline_GCD_hash:
                raise RuntimeError(f"Existing baseline GCD in cache (SHA1 {cached_baseline_GCD_hash}) and packet from input (SHA1 {baseline_GCD_hash}) differ.")
            LOGGER.debug("Checked baseline GCD against existing data in cache: consistent.")
        else:
            save_GCD_frame_packet_to_file(baseline_GCD_framepacket, cached_baseline_GCD_file)
            LOGGER.debug(f"Wrote baseline GCD frames to {cached_baseline_GCD_file}.")

        # baseline_GCD path is saved in a text file
        source_baseline_GCD_metadata = os.path.join(event_cache_dir, cfg.SOURCE_BASELINE_GCD_METADATA)
        if os.path.isfile(source_baseline_GCD_metadata):
            with open(source_baseline_GCD_metadata, 'r') as f:
                filename = f.read()
            if (filename != baseline_GCD) and (os.path.basename(filename) != os.path.basename(baseline_GCD)):
                raise RuntimeError(f"Expected the stored source baseline GCD to be {baseline_GCD}. It is {filename}.")
        with open(source_baseline_GCD_metadata, "w") as text_file:
            text_file.write(baseline_GCD)   

    #=====================
    # GCD-less framepacket
    #=====================
    if ("I3Geometry" not in frame_packet[0]) and ("I3GeometryDiff" not in frame_packet[0]):
        LOGGER.debug("Packet with empty GCD frames. Need to load baseline GCD")
        # If no GCD is specified, work out correct one from run number
        available_GCDs = sorted([x for x in os.listdir(GCD_dir) if ".i3" in x])
        run = float(header.run_id)
        latest = available_GCDs[0]
        for x in available_GCDs:
            if "Run" in x:
                if run > float(x.split("_")[3][3:-3]):
                    latest = x
            elif "baseline" in x:
                if run > float(x.split("_")[2][:-3]):
                    latest = x

        baseline_GCD_file = os.path.join(GCD_dir, latest)

        LOGGER.debug((available_GCDs, run))
        LOGGER.debug(f"By process of elimination using run numbers, using {baseline_GCD_file}")
        baseline_GCD_framepacket = load_framepacket_from_file(baseline_GCD_file)
        for i in (0,1,2):
            frame_packet[i] = baseline_GCD_framepacket[i]
        del baseline_GCD_framepacket

    if baseline_GCD is not None:
        # frame_packet has GCD diff, provide baseline
        frame_packet = prepare_frames(frame_packet, baseline_GCD_file, reco_algo, pulsesName=pulsesName)
    else:
        # frame_packet has either normal GCD or has been reassembled
        frame_packet = prepare_frames(frame_packet, None, reco_algo, pulsesName=pulsesName)

    # move the last packet frame from Physics to the 'p' stream
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('p'))

    cached_GCDQp = os.path.join(event_cache_dir, cfg.GCDQp_FILENAME)

    if os.path.exists(cached_GCDQp):
        # GCD already exists - check to make sure it is consistent
        GCDQp_framepacket_hash = hash_frame_packet(frame_packet)
        cached_QCDQp_framepacket = load_framepacket_from_file(cached_GCDQp)
        cached_GCDQp_framepacket_hash = hash_frame_packet(cached_QCDQp_framepacket)
        if GCDQp_framepacket_hash != cached_GCDQp_framepacket_hash:
            raise RuntimeError(f"Existing GCDQp packet in cache (SHA1 {cached_GCDQp_framepacket_hash}) and packet from input (SHA1 {GCDQp_framepacket_hash}) differ.")
        LOGGER.debug("Checked dependency against cached GCDQp: consistent.")
    else:
        # no GCD exists yet
        save_GCD_frame_packet_to_file(frame_packet, cached_GCDQp)
        LOGGER.debug(f"Wrote GCDQp dependency frames to {cached_GCDQp}.")

    return (
        event_cache_dir,
        event_metadata,
        {
            cfg.STATEDICT_GCDQP_PACKET: frame_packet,
            cfg.STATEDICT_BASELINE_GCD_FILE: baseline_GCD_file
        },
    )
