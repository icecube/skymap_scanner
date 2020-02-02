#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import

import pulsar

import os
import sys
import logging
import json
import healpy

# Python 2 and 3:
try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError
    
from icecube import icetray, dataclasses, dataio

from extract_json_message import extract_json_message
from prepare_frames import prepare_frames
from utils import get_MC_truth, get_event_id, get_event_time

from send_scan import send_scan
from scan_pixel import scan_pixel
from collect_pixels import collect_pixels
from save_pixels import save_pixels
from extract_i3_file import extract_i3_file

def producer(eventURL, broker, auth_token, topic, metadata_topic_base, event_name, nside, area_center_nside=None, area_center_pixel=None, area_num_pixels=None):
    """
    Handle incoming events and perform a full scan.
    """
    if (area_center_nside is not None or area_center_pixel is not None or area_num_pixels is not None) and \
       (area_center_nside is None or area_center_pixel is None or area_num_pixels is None):
       raise RuntimeError("You have to either set none of the three options area_center_nside,area_center_pixel,area_num_pixels or all of them")

    try:
        # figure out if this is supposed to be JSON or .i3:
        url_file_path = urlparse(eventURL).path
        file_name, file_ext = os.path.splitext(url_file_path)
        if file_ext == '.json':
            file_format = 'json'
        elif file_ext == '.i3':
            file_format = 'i3'
        elif file_ext in ['.zst', '.gz', '.bz2', '.xz']:
            file_name, file_ext2 = os.path.splitext(file_name)
            if file_ext2 == '.i3':
                file_format = 'i3'
            else:
                raise RuntimeError("File format {}.{} is unknown (url={})".format(file_ext2, file_ext, eventURL))
        else:
            raise RuntimeError("File format {} is unknown (url={})".format(file_ext, eventURL))
            
        # load JSON
        if file_format == 'json':
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
            
            # Note: the online messages to not use pulse cleaning, so we will need to work with
            # "SplitUncleanedInIcePulses" instead of "SplitInIcePulses" as the P-frame pulse map.
            # (Setting `pulsesName` will make sure "SplitInIcePulses" gets created and just points
            # to "SplitUncleanedInIcePulses".)
            pulsesName="SplitUncleanedInIcePulses"
        else: # file_format == 'i3'
            print('Skymap scanner is starting. Reading event information from i3 file at `{0}`.'.format(eventURL))
            GCDQp_packet = extract_i3_file( eventURL )

            pulsesName="SplitInIcePulses"
        
        # This step will create missing frame objects if necessary.
        print('Event extracted. I will now perform some simple tasks like the HESE veto calculation...')
        GCDQp_packet = prepare_frames(GCDQp_packet, pulsesName=pulsesName)
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
            nside=nside,
            area_center_nside=area_center_nside,
            area_center_pixel=area_center_pixel,
            area_num_pixels=area_num_pixels
            )

        print("All scans for `{0}` are submitted.".format(event_id))
    except:
        exception_message = str(sys.exc_info()[0])+'\n'+str(sys.exc_info()[1])+'\n'+str(sys.exc_info()[2])
        print('Something went wrong while scanning the event (python caught an exception): ```{0}```'.format(exception_message))
        raise # re-raise exceptions


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog <producer|worker> [options] <master:eventURL>"""
    parser.set_usage(usage)
    parser.add_option("-t", "--topic_in", action="store", type="string",
        default="persistent://icecube/skymap/to_be_scanned",
        dest="TOPICIN", help="The Pulsar topic name for pixels to be scanned")
    parser.add_option("-m", "--topic_meta", action="store", type="string",
        default="persistent://icecube/skymap_metadata/mf_",
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
        default=None,
        dest="NSIDE", help="Healpix NSide, determining the number of pixels to scan.")

    parser.add_option("--area", action='callback', type='string',
        callback=lambda option, opt, value, parser: setattr(parser.values, option.dest, value.split(',')),
        dest="AREA", help="Optional: the area to scan: <center_nside,center_pix,num_pix>")

    parser.add_option("-n", "--name", action="store", type="string",
        default=None,
        dest="NAME", help="The unique event name. Will be appended to all topic names so that multiple scans can happen in parallel. Make sure you use different names for different events.")

    parser.add_option("--delete-output-from-queue", action="store_true",
        dest="DELETE_OUTPUT_FROM_QUEUE", help="When saving the output to a file, delete pixels from the queue once they have been written. They cannot be written a second time in that case.")

    parser.add_option("--fake-scan", action="store_true",
        dest="FAKE_SCAN", help="Just return random numbers and wait 1 second instead of performing the actual calculation in the worker. For testing only.")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) < 1:
        raise RuntimeError("You need to specify a mode <producer|worker>")
    mode = args[0].lower()
    
    topic_base_meta = options.TOPICMETA
    topic_in        = options.TOPICIN
    topic_out       = options.TOPICOUT
    topic_base_col  = options.TOPICCOL
    
    if mode == "producer":
        if len(args) != 2:
            raise RuntimeError("You need to specify an input file URL in `producer` mode")

        if options.NAME is None:
            raise RuntimeError("You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector.")

        if options.NSIDE is None:
            raise RuntimeError("You need to explicitly specify an --nside value when in `producer` mode.")
            
        if not healpy.isnsideok(options.NSIDE):
            raise RuntimeError("--nside {} is invalid.".format(options.NSIDE))
        
        if options.AREA is not None:
            if len(options.AREA) != 3:
                raise RuntimeError("--area must be configured with a list of length 3: --area <center_nside,center_pix,num_pix>")

            area_center_nside=int(options.AREA[0])
            area_center_pixel=int(options.AREA[1])
            area_num_pixels=int(options.AREA[2])

            if not healpy.isnsideok(area_center_nside):
                raise RuntimeError("--area center pixel nside {} is invalid.".format(area_center_nside))
                
            area_center_nside_npix = healpy.nside2npix(area_center_nside)
            if area_center_pixel >= area_center_nside_npix:
                raise RuntimeError("--area center pixel number {} is invalid (valid range=0..{}).".format(area_center_pixel, area_center_nside_npix-1))
                
            if area_num_pixels <= 0:
                raise RuntimeError("--area pixel number cannot be zero or negative!")
        else:
            area_center_nside=None
            area_center_pixel=None
            area_num_pixels=None
            
        nside = options.NSIDE
        npixels = 12 * (nside**2)

        print("Scanning NSide={}, corresponding to NPixel={}".format(nside, npixels))

        eventURL = args[1]
        producer(eventURL, broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic=topic_in, metadata_topic_base=topic_base_meta, event_name=options.NAME, nside=nside, area_center_nside=area_center_nside, area_center_pixel=area_center_pixel, area_num_pixels=area_num_pixels)
    elif mode == "worker":
        scan_pixel(broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic_in=topic_in, topic_out=topic_out, fake_scan=options.FAKE_SCAN)
    elif mode == "collector":
        collect_pixels(broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic_in=topic_out, topic_base_out=topic_base_col)
    elif mode == "saver":
        if options.NAME is None:
            raise RuntimeError("You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector.")

        if options.NSIDE is None:
            nsides = None
        else:
            nside = options.NSIDE
            npixels = 12 * (nside**2)
            print("Waiting for all pixels for NSide={}, corresponding to NPixel={}".format(nside, npixels))
            nsides = [nside]

        save_pixels(broker=options.BROKER, auth_token=options.AUTH_TOKEN, topic_in=topic_base_col+options.NAME, filename_out=options.OUTPUT, nsides_to_wait_for=nsides, delete_from_queue=options.DELETE_OUTPUT_FROM_QUEUE)
    else:
        raise RuntimeError("Unknown mode \"{}\"".args[0])
