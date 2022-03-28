#!/usr/bin/env python

# fmt: off
# isort: skip_file

import os
import sys
import logging
import json

from icecube import icetray, dataclasses, dataio
from skymap_scanner import extract_json_message, perform_scan, create_plot
from skymap_scanner import slack_tools
from skymap_scanner import scan_pixel_distributed_client

def post_to_slack(text):
    print(text)
    return
    # never crash because of Slack
    try:
        logger = logging.getLogger()
        logger.info(text)
        return slack_tools.post_message(text)
    except:
        pass

def skymap_plotting_callback(event_id, state_dict):
    return
    post_to_slack("I am creating a plot of the current status of the scan of `{0}` for you. This should only take a minute...".format(event_id))

    # create a plot when done and upload it to slack
    plot_png_buffer = create_plot(event_id, state_dict)

    # we have a buffer containing a valid png file now, post it to Slack
    slack_tools.upload_file(plot_png_buffer, "skymap_{0}.png".format(event_id), "Skymap of {0}".format(event_id))

def incoming_event(eventURL, base_GCD_path, cache_dir, port):
    """
    Handle incoming events and perform a full scan.
    """
    try:
        # get a file stager
        stagers = dataio.get_stagers()

        post_to_slack('Skymap scanner is starting. Reading event information from JSON blob at `{0}`.'.format(eventURL))

        post_to_slack("reading JSON blob from {0}".format( eventURL ))
        json_blob_handle = stagers.GetReadablePath( eventURL )
        if not os.path.isfile( str(json_blob_handle) ):
            post_to_slack("problem reading JSON blob from {0}".format( eventURL ))
            raise RuntimeError("problem reading JSON blob from {0}".format( eventURL ))
        with open( str(json_blob_handle) ) as json_data:
            event = json.load(json_data)
        del json_blob_handle

        post_to_slack('Event loaded. I am extracting it now...')

        # extract the JSON message
        event_id, state_dict = extract_json_message(event, filestager=stagers, base_GCD_path=base_GCD_path, cache_dir=cache_dir)

        # try to get the event time
        p_frame = state_dict['GCDQp_packet'][-1]
        if "I3EventHeader" not in p_frame:
            post_to_slack("Something is wrong with this event (ID `{0}`). Its P-frame doesn't have a header... I will try to continue with submitting the scan anyway, but this doesn't look good.".format(event_id))
        else:
            time = p_frame["I3EventHeader"].start_time
            post_to_slack("Event `{0}` happened at `{1}`. I will now attempt to submit a full-sky millipede scan.".format(event_id, str(time)))

        post_to_slack("Starting scan...")

        # now perform the actual scan
        state_dict = perform_scan(
            event_id_string=event_id,
            state_dict=state_dict,
            cache_dir=cache_dir,
            base_GCD_path=base_GCD_path,
            port=port,
            logger=post_to_slack, # logging callback
            skymap_plotting_callback = lambda d: skymap_plotting_callback(event_id, d)
        )

        post_to_slack("Scanning of `{0}` is done. Let me create a plot for you real quick.".format(event_id))

        # create a plot when done and upload it to slack
        skymap_plotting_callback(event_id, state_dict)

        post_to_slack("Okay, that's it. The event scan is done.")
    except:
        exception_message = str(sys.exc_info()[0])+'\n'+str(sys.exc_info()[1])+'\n'+str(sys.exc_info()[2])
        post_to_slack('Something went wrong while scanning the event (python caught an exception): ```{0}```'.format(exception_message))
        raise # re-raise exceptions


if __name__ == "__main__":
    from optparse import OptionParser
    from skymap_scanner.load_scan_state import load_cache_state

    parser = OptionParser()
    usage = """%prog <master|worker> [options] event_URL/master_IP"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="/cache", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("-g", "--base-gcd-path", action="store", type="string",
        default="/opt/i3-data/baseline_gcds", dest="BASEGCDPATH", help="The path where baseline GCD files are stored")
    parser.add_option("-p", "--port", action="store", type="int",
        default=12345, dest="PORT", help="The tcp port to use")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 2:
        raise RuntimeError("You need to specify a mode and an event URL/master IP")
    
    mode = args[0].lower()
    if mode == "master":
        eventURL = args[1]
        incoming_event(eventURL, base_GCD_path=options.BASEGCDPATH, cache_dir=options.CACHEDIR, port=options.PORT)
    elif mode == "worker":
        serverAddress = args[1]
        scan_pixel_distributed_client(port=options.PORT, server=serverAddress, base_GCD_path=options.BASEGCDPATH)
    else:
        raise RuntimeError("Unknown mode \"{}\"".args[0])
