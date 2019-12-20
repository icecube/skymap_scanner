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

def producer(eventURL, broker, topic, metadata_topic):
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

        full_topic = topic #+'-'+event_id
        full_metadata_topic = metadata_topic #+'-'+event_id

        print("Publishing events to   {}".format(full_topic))
        print("Publishing metadata to {}".format(full_metadata_topic))

        print("Submitting scan...")
        send_scan(
            frame_packet=GCDQp_packet,
            broker=broker, 
            topic=full_topic,
            metadata_topic=full_metadata_topic)

        print("All scans for `{0}` are submitted.".format(event_id))
    except:
        exception_message = str(sys.exc_info()[0])+'\n'+str(sys.exc_info()[1])+'\n'+str(sys.exc_info()[2])
        print('Something went wrong while scanning the event (python caught an exception): ```{0}```'.format(exception_message))
        raise # re-raise exceptions

def worker(broker, topic_in, topic_out):
    scan_pixel(
        broker=broker, 
        topic_in=topic_in,
        topic_out=topic_out,
        )

def collector(broker, topic_in, topic_out):
    collect_pixels(
        broker=broker, 
        topic_in=topic_in,
        topic_out=topic_out,
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
        default="persistent://icecube/skymap_metadata/metadata_frames",
        dest="TOPICMETA", help="The Pulsar topic name for metadata frames such as G,C,D,Q,p")
    parser.add_option("-s", "--topic_out", action="store", type="string",
        default="persistent://icecube/skymap/scanned",
        dest="TOPICOUT", help="The Pulsar topic name for pixels that have been scanned")
    parser.add_option("-c", "--topic_col", action="store", type="string",
        default="persistent://icecube/skymap/collected",
        dest="TOPICCOL", help="The Pulsar topic name for pixels that have been collected (each pixel is scanned several times with different seeds, this has the \"best\" result only)")
    parser.add_option("-b", "--broker", action="store", type="string",
        default="pulsar://localhost:6650",
        dest="BROKER", help="The Pulsar broker URL to connect to")

    parser.add_option("-n", "--name", action="store", type="string",
        default=None,
        dest="NAME", help="The unique event name. Will be appended to all topic names so that multiple scans can happen in parallel. Make sure you use different names for different events.")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) < 1:
        raise RuntimeError("You need to specify a mode <producer|worker>")
    mode = args[0].lower()
    
    if options.NAME is None:
        raise RuntimeError("You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector.")
    
    topic_meta = options.TOPICMETA + '-' + options.NAME
    topic_in   = options.TOPICIN   + '-' + options.NAME
    topic_out  = options.TOPICOUT  + '-' + options.NAME
    topic_col  = options.TOPICCOL  + '-' + options.NAME
    
    if mode == "producer":
        if len(args) != 2:
            raise RuntimeError("You need to specify a input file URL in `producer` mode")

        eventURL = args[1]
        producer(eventURL, broker=options.BROKER, topic=topic_in, metadata_topic=topic_meta)
    elif mode == "worker":
        worker(broker=options.BROKER, topic_in=topic_in, topic_out=topic_out)
    elif mode == "collector":
        collector(broker=options.BROKER, topic_in=topic_out, topic_out=topic_col)
    else:
        raise RuntimeError("Unknown mode \"{}\"".args[0])
