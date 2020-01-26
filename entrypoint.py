#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import

import pulsar


import os
import sys
import logging
import json

from icecube import icetray, dataclasses, dataio

from extract_json_message import extract_json_message
from prepare_frames import prepare_frames
from utils import get_MC_truth, get_event_id, get_event_time

from send_scan import send_scan
from scan_pixel import scan_pixel
from collect_pixels import collect_pixels
from save_pixels import save_pixels

def producer(eventURL, broker, auth_token, topic, metadata_topic_base, event_name, nside):
    """
    Handle incoming events and perform a full scan.
    """
    try:
        # get a file stager
        stagers = dataio.get_stagers()

        print('Skymap scanner is starting. Reading event information from JSON blob at `{0}`.'.format(eventURL))

        print("reading JSON blob from {0}".format( eventURL ))
        json_blob_handle = stagers.GetReadablePath( eventURL )
        if not os.path.isfile( str(json_blob_handle) ):
            print("problem reading JSON blob from {0}".format( eventURL ))
            raise RuntimeError("problem reading JSON blob from {0}".format( eventURL ))
        with open( str(json_blob_handle) ) as json_data:
            json_event = json.load(json_data)
        del json_blob_handle

        # extract the JSON message
        print('Event loaded. I am extracting it now...')
        GCDQp_packet = extract_json_message(json_event)
        
        # this will create missing frame objects if necessary
        print('Event extracted. I will now perform some simple things like the HESE veto calculation...')
        GCDQp_packet = prepare_frames(GCDQp_packet)
        print('Done.')
        
        # get the event id
        event_id = get_event_id(GCDQp_packet)

        # get the event time
        time = get_event_time(GCDQp_packet)

        print("Event `{0}` happened at `{1}`.".format(event_id, str(time)))

        print("Publishing events to   {}".format(topic))
        print("Publishing metadata to {}<...>".format(metadata_topic_base))

        print("Submitting scan...")
        send_scan(
            frame_packet=GCDQp_packet,
            broker=broker, 
            auth_token=auth_token,
            topic=topic,
            metadata_topic_base=metadata_topic_base,
            event_name=event_name,
            nside=nside)

        print("All scans for `{0}` are submitted.".format(event_id))
    except:
        exception_message = str(sys.exc_info()[0])+'\n'+str(sys.exc_info()[1])+'\n'+str(sys.exc_info()[2])
        print('Something went wrong while scanning the event (python caught an exception): ```{0}```'.format(exception_message))
        raise # re-raise exceptions

def worker(broker, auth_token, topic_in, topic_out, fake_scan):
    scan_pixel(
        broker=broker, 
        auth_token=auth_token,
        topic_in=topic_in,
        topic_out=topic_out,
        fake_scan=fake_scan,
        )

def collector(broker, auth_token, topic_in, topic_base_out):
    collect_pixels(
        broker=broker, 
        auth_token=auth_token,
        topic_in=topic_in,
        topic_base_out=topic_base_out,
        )

def saver(broker, auth_token, topic_in, filename_out, expected_n_frames, delete_from_queue):
    save_pixels(
        broker=broker, 
        auth_token=auth_token,
        topic_in=topic_in,
        filename_out=filename_out,
        expected_n_frames=expected_n_frames,
        delete_from_queue=delete_from_queue
        )

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog <producer|worker> [options] <master:eventURL>"""
    parser.set_usage(usage)
    parser.add_option("-t", "--topic_in", action="store", type="string",
        default="persistent://icecube/skymap/to_be_scanned",
        dest="TOPICIN", help="The Pulsar topic name for pixels to be scanned")
    parser.add_option("-m", "--topic_meta", action="store", type="string",
        default="persistent://icecube/skymap_metadata/metadata_frames_",
        dest="TOPICMETA", help="The Pulsar topic name for metadata frames such as G,C,D,Q,p")
    parser.add_option("-s", "--topic_out", action="store", type="string",
        default="persistent://icecube/skymap/scanned",
        dest="TOPICOUT", help="The Pulsar topic name for pixels that have been scanned")
    parser.add_option("-c", "--topic_col", action="store", type="string",
        default="persistent://icecube/skymap/collected_",
        dest="TOPICCOL", help="The Pulsar topic name for pixels that have been collected (each pixel is scanned several times with different seeds, this has the \"best\" result only)")
    parser.add_option("-b", "--broker", action="store", type="string",
        default="pulsar://localhost:6650",
        dest="BROKER", help="The Pulsar broker URL to connect to")
    parser.add_option("-a", "--auth-token", action="store", type="string",
        default=None,
        dest="AUTH_TOKEN", help="The Pulsar authentication token to use")

    parser.add_option("-o", "--output", action="store", type="string",
        default="final_output.i3",
        dest="OUTPUT", help="Name of the output .i3 file written by the \"saver\".")

    parser.add_option("-i", "--nside", action="store", type="int",
        default=1,
        dest="NSIDE", help="Healpix NSide, determining the number of pixels to scan.")

    parser.add_option("-n", "--name", action="store", type="string",
        default=None,
        dest="NAME", help="The unique event name. Will be appended to all topic names so that multiple scans can happen in parallel. Make sure you use different names for different events.")

    parser.add_option("--delete-output-from-queue", action="store_true",
        dest="DELETE_OUTPUT_FROM_QUEUE", help="When saving the output to a file, delete pixels from the queue once they have been written. They cannot be written a second time in that case.")

    parser.add_option("--fake-scan", action="store_true",
        dest="FAKE_SCAN", help="Just return random numbers and wait 1 second instead of performing the actula calculation in the worker. For testing only.")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) < 1:
        raise RuntimeError("You need to specify a mode <producer|worker>")
    mode = args[0].lower()
    
    topic_base_meta = options.TOPICMETA
    topic_in        = options.TOPICIN
    topic_out       = options.TOPICOUT
    topic_base_col  = options.TOPICCOL
    
    nside = options.NSIDE
    npixels = 12 * (nside**2)
    
    if mode == "producer":
        if len(args) != 2:
            raise RuntimeError("You need to specify a input file URL in `producer` mode")

        if options.NAME is None:
            raise RuntimeError("You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector.")

        print("Scanning NSide={}, corresponding to NPixel={}".format(nside, npixels))

        eventURL = args[1]
        producer(eventURL, broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic=topic_in, metadata_topic_base=topic_base_meta, event_name=options.NAME, nside=nside)
    elif mode == "worker":
        worker(broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic_in=topic_in, topic_out=topic_out, fake_scan=options.FAKE_SCAN)
    elif mode == "collector":
        collector(broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic_in=topic_out, topic_base_out=topic_base_col)
    elif mode == "saver":
        if options.NAME is None:
            raise RuntimeError("You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector.")

        print("Scanning NSide={}, corresponding to NPixel={}".format(nside, npixels))

        saver(broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic_in=topic_base_col+options.NAME, filename_out=options.OUTPUT, expected_n_frames=npixels, delete_from_queue=options.DELETE_OUTPUT_FROM_QUEUE)
    else:
        raise RuntimeError("Unknown mode \"{}\"".args[0])
