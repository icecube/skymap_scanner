"""Tools for extracting json messages."""

# fmt: off
# pylint: skip-file

import json
import os
from typing import Tuple

import numpy as np
from icecube import dataio, full_event_followup, icetray  # type: ignore[import]

from .. import config as cfg
from . import LOGGER
from .event_tools import EventMetadata
from .load_scan_state import load_scan_state
from .prepare_frames import prepare_frames
from .utils import (
    get_event_mjd,
    hash_frame_packet,
    load_GCD_frame_packet_from_file,
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
    filestager,
    is_real_event: bool,
    cache_dir="./cache/",
    GCD_dir=None,
) -> Tuple[EventMetadata, dict]:
    if not os.path.exists(cache_dir):
        raise RuntimeError("cache directory \"{0}\" does not exist.".format(cache_dir))
    if not os.path.isdir(cache_dir):
        raise RuntimeError("cache directory \"{0}\" is not a directory.".format(cache_dir))

    # extract the packet
    frame_packet = full_event_followup.i3live_json_to_frame_packet(json.dumps(json_data), pnf_framing=True)

    _, event_metadata, state_dict = __extract_frame_packet(
        frame_packet,
        filestager=filestager,
        reco_algo=reco_algo,
        is_real_event=is_real_event,
        cache_dir=cache_dir,
        GCD_dir=GCD_dir,
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
    filestager,
    reco_algo: str,
    is_real_event: bool,
    cache_dir="./cache/",
    GCD_dir=None,
    pulsesName="SplitUncleanedInIcePulses",
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
        raise RuntimeError("No I3EventHeader in Physics frame")
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
    this_event_cache_dir = os.path.join(cache_dir, str(event_metadata))
    if os.path.exists(this_event_cache_dir) and not os.path.isdir(this_event_cache_dir):
        raise RuntimeError("this event would be cached in directory \"{0}\", but it exists and is not a directory".format(this_event_cache_dir))
    if not os.path.exists(this_event_cache_dir):
        os.mkdir(this_event_cache_dir)

    # see if we have the required baseline GCD to which to apply the GCD diff
    
    baseline_GCD = extract_GCD_diff_base_filename(frame_packet)

    LOGGER.debug(f"Extracted GCD_diff_base_filename = {baseline_GCD}.")
    LOGGER.debug(f"GCD dir is set to = {GCD_dir}.")

    if baseline_GCD is not None:
        if GCD_dir is not None: # always true when the arg is passed!
            baseline_GCD_file = os.path.join(GCD_dir, baseline_GCD)
            LOGGER.debug("Trying GCD file: {baseline_GCD_file}")
            if os.path.isfile(baseline_GCD_file):
                baseline_GCD = baseline_GCD_file
                GCD_dir = baseline_GCD_file
            else:
                LOGGER.debug("Baseline GCD file not available!")
            # if the baseline GCD is found: GCD_dir == baseline_GCD == baseline_GCD_file
            # else: - GCD_dir comes from the args
            #       - baseline_GCD is still the one derived from the frame packet
            #       - baseline_GCD_file is a path (not necessarily valid)
            # confusing enough!

        # NOTE: logic allowing GCD_dir to point to a file, in order to directly override the GCD has been removed.
        # "Polymorphic variables" are a bad idea!

        LOGGER.debug(f"Packet needs to load GCD diff based on file \"{baseline_GCD}\"")

        # NOTE: we used to loop over a set of possible GCD_BASE_DIRS but it is no longer the case.
        # The following conditional structure could be a bit smarter.
        try:
            LOGGER.debug("reading GCD from {baseline_GCD_file}")
            GCD_diff_base_handle = filestager.GetReadablePath(baseline_GCD_file)
            if not os.path.isfile(str(GCD_diff_base_handle)):
                raise RuntimeError("File does not exist (or is not a file)")
        except:
            # why this is not an if-then? could GetReadablePath throw an exception?
            LOGGER.debug(" -> failed")
            GCD_diff_base_handle = None
            
        if GCD_diff_base_handle is not None:
            LOGGER.debug(" -> success")
        else:
            raise RuntimeError("Could not read the input GCD file \"{baseline_GCD}\"")
            
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
            LOGGER.debug("checked baseline GCD against existing data in cache - consistent")
        else:
            save_GCD_frame_packet_to_file(diff_referenced, new_GCD_base_filename)
            LOGGER.debug("wrote baseline GCD frames to {0}".format(new_GCD_base_filename))

        # save the GCD filename
        original_GCD_diff_base_filename = os.path.join(this_event_cache_dir, "original_base_GCD_for_diff_filename.txt")
        if os.path.isfile(original_GCD_diff_base_filename):
            f = open(original_GCD_diff_base_filename, 'r')
            filename = f.read()
            del f
            if np.logical_and(
                    filename != baseline_GCD,
                    os.path.basename(filename) != os.path.basename(baseline_GCD)):
                raise RuntimeError("expected the stored GCD base filename to be {0}. It is {1}.".format(baseline_GCD, filename))
        with open(original_GCD_diff_base_filename, "w") as text_file:
            text_file.write(baseline_GCD)
    else:
        LOGGER.debug("packet does not need a GCD diff")

    # special case for old EHE alerts with empty GCD frames
    if ("I3Geometry" not in frame_packet[0]) and ("I3GeometryDiff" not in frame_packet[0]):

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

        GCD_dir = os.path.join(GCD_dir, latest)

        LOGGER.debug((available_GCDs, run))
        LOGGER.debug("********** old EHE packet with empty GCD frames. need to replace all geometry. ********")
        LOGGER.debug("By process of elimination using run numbers, using {0}".format(GCD_dir))
        if GCD_dir is None:
            raise RuntimeError("Cannot continue - don't know which GCD to use for empty GCD EHE event. Please set override_GCD_filename.")
        ehe_override_gcd = load_GCD_frame_packet_from_file(GCD_dir)
        frame_packet[0] = ehe_override_gcd[0]
        frame_packet[1] = ehe_override_gcd[1]
        frame_packet[2] = ehe_override_gcd[2]
        del ehe_override_gcd

    if baseline_GCD is not None:
        frame_packet = prepare_frames(frame_packet, str(GCD_diff_base_handle), reco_algo, pulsesName=pulsesName)
    else:
        frame_packet = prepare_frames(frame_packet, None, reco_algo, pulsesName=pulsesName)

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
        LOGGER.debug("checked dependency against existing data in cache - consistent")
    else:
        # no GCD exists yet
        save_GCD_frame_packet_to_file(frame_packet, GCDQp_filename)
        LOGGER.debug("wrote GCDQp dependency frames to {0}".format(GCDQp_filename))

    return (
        this_event_cache_dir,
        event_metadata,
        {
            cfg.STATEDICT_GCDQP_PACKET: frame_packet,
            cfg.STATEDICT_BASELINE_GCD_FILE: baseline_GCD
        },
    )
