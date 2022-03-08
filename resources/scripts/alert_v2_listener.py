#!/usr/bin/env python

import os
import sys
import logging
import math
import random
import shutil
import datetime
import pickle as Pickle
import numpy as np

import argparse

from icecube import dataclasses, dataio, realtime_tools, astro
from icecube.skymap_scanner import extract_json_message, create_plot, \
    perform_scan, config, loop_over_plots, get_best_fit_v2
from icecube.skymap_scanner import slack_tools
from icecube.skymap_scanner.utils import create_event_id
from icecube.skymap_scanner.scan_logic import whether_to_scan, stream_logic_map, extract_short_message

from listener_conf import *

# ==============================================================================
# Configure Slack posting settings
# ==============================================================================

def post_to_slack(text):
    # never crash because of Slack
    try:
        logger = logging.getLogger()
        logger.info(text)
        return slack_tools.post_message(text)
    except Exception as err:
        logger.warning(f"Posting to Slack failed because of: {err}")

# ==============================================================================
# If operating on cobalt machines, ssh into submitter
# otherwise, submit from the followup machines directly
# ==============================================================================

if realtime_tools.config.NAME == "PRIVATE":
    submit_prefix = "ssh submitter"
else:
    submit_prefix = ""

# ==============================================================================
# Configure and prepare cache dir
# ==============================================================================

event_cache_dir = os.path.join(realtime_tools.config.SCRATCH, "skymap_scanner_cache/")

try:
    os.makedirs(event_cache_dir)
except OSError:
    pass

submit_file = os.path.dirname(os.path.abspath(__file__)) + "/spawn_session.sh"

# ==============================================================================
# Set up unique port number, so that overlapping alerts have different ports
# ==============================================================================

def port_number():
    """Assuming that scans do not take longer than a day, and that scanned
    must be sent out in order, then the number of seconds since midnight will
    be a unique 5 figure port number

    :return: Port number (n seconds since midnight)
    """
    now = datetime.datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (now - midnight).seconds
    return '{:05d}'.format(seconds)

# ==============================================================================
# Function to factor out into separate scanner script
# ==============================================================================

def skymap_plotting_callback(event_id, state_dict):
    post_to_slack(
        "I am creating a plot of the current status of the scan of `{0}` for you. This should only take a minute...".format(
            event_id))

    # create a plot when done and upload it to slack
    plot_png_buffer = create_plot(event_id, state_dict)

    # we have a buffer containing a valid png file now, post it to Slack
    slack_tools.upload_file(plot_png_buffer, "skymap_{0}.png".format(event_id),
                            "Skymap of {0}".format(event_id))


def spawn_scan(post_to_slack, short_message=None, **kwargs):

    def finish_function(state_dict):
        try:
            alert_eval = short_message
            ra = np.degrees(alert_eval["ra"])
            dec = np.degrees(alert_eval["dec"])
            rad = np.degrees(alert_eval["err_50"])
        except:
            ra = np.nan
            dec = np.nan
            rad = np.nan
        #post_to_slack("Ra: {0}, Dec: {1}, Rad: {2}".format(ra, dec, rad))

        post_to_slack(
            "Scanning of `{0}` is done. Let me create a plot for you real quick.".format(
                kwargs["event_id_string"]))

        def upload_func(png_buffer, filename, title):
            slack_tools.upload_file(png_buffer, filename, title)
        
        def log_func(text):
            for i,ch in enumerate(final_channels):
                config.slack_channel=ch
                post_to_slack(text)
         
        event_id = kwargs["event_id_string"]
        loop_over_plots(event_id, state_dict=state_dict, cache_dir=event_cache_dir, ra=ra, dec=dec, radius=rad, log_func=log_func, upload_func=upload_func, final_channels=final_channels)
        
        try:
            get_best_fit_v2(event_id, cache_dir=event_cache_dir, log_func=log_func)
        except:
            pass

        post_to_slack(
            "Okay, that's it. I'm finished with this `{0}`. Look for the cache in `{1}`".format(event_id, event_cache_dir))

    # # now perform the actual scan
    state_dict = perform_scan(finish_function=finish_function, **kwargs)

# ==============================================================================
# Function to run on each incoming alert
# ==============================================================================
def incoming_event(varname, topics, event):
    individual_event(event)

def individual_event(event):

    try:

        # first check if we are supposed to work on this specific kind of alert
        if "value" not in event:
            post_to_slack(
                'incoming message is invalid - no key named "value" in message')
            return
        if "streams" not in event["value"]:
            post_to_slack(
                'incoming message is invalid - no key named "streams" in event["value"]')
        alert_streams = [str(x) for x in event["value"]["streams"]]

        matched_keys = [x for x in list(stream_logic_map.keys())
                        if x in alert_streams]

        if len(matched_keys) == 0:
            #post_to_slack('Ignoring event tagged with streams: `{0}`'.format(
            #    alert_streams))
            return  # do not scan

        # get a file stager
        stagers = dataio.get_stagers()

        # extract the JSON message
        event_id, state_dict = extract_json_message(
            event, filestager=stagers,
            cache_dir=event_cache_dir,
            override_GCD_filename=gcd_dir
        )

        [run, evt, _] = event_id.split(".")

        short_message = None
        try:
            if "reco" in list(event["value"]["data"].keys()):
                short_message = dict(value=dict(data=event["value"]["data"]))
                del short_message["value"]["data"]["frames"]
        except:
            pass

        # Post a slack message for non-GFU-only events

        if alert_streams != ["neutrino"]:

            post_to_slack(
                'New event found, `{0}`, `{1}`, tagged with alert '
                'streams: `{2}`'.format(run, evt, alert_streams))

        # Post a Slack message for a random subset of GFU-only events

        elif (random.random() * gfu_prescale) < 1.:
            post_to_slack(
                "New GFU-only event found, `{0}`, `{1}`, with Passing "
                "Faction: {2}. "
                "It's probably sub-threshold, but I'll check it anyway. *sigh*".format(
                    run, evt, 1./gfu_prescale))

        # try to get the event time
        p_frame = state_dict['GCDQp_packet'][-1]
        if "I3EventHeader" not in p_frame:
            post_to_slack(
                "Something is wrong with this event (ID `{0}`). Its P-frame "
                "doesn't have a header... I will try to continue with "
                "submitting the scan anyway, but this doesn't look good.".format(
                    event_id))

        # Determine whether event should be scanned or not

        do_scan = whether_to_scan(p_frame, alert_streams, notify_alert,
                                  post_to_slack, short_message)

        # If event should not be scanned, do not scan. Post a message to
        # slack, unless the event is GFU-only

        if not do_scan:

            # Only notify if event is not GFU-only

            if alert_streams != ["neutrino"]:
                post_to_slack("This event is subthreshold. No scan is needed.")

            # Delete file (which can be ~40Mb each!!!)

            shutil.rmtree(os.path.join(event_cache_dir, event_id))

            return # do not scan

        try:
            for f in stream_logic_map.values():
                if short_message is None:
                    short_message = f(extract_short_message(p_frame, post_to_slack))
        except:
            pass

        spawn_scan(
            post_to_slack,
            event_id_string=event_id,
            state_dict=state_dict,
            cache_dir=event_cache_dir,
            port=port_number(),
            numclients=distribute_numclients,
            logger=post_to_slack,  # logging callback
            skymap_plotting_callback=lambda d: skymap_plotting_callback(
                event_id, d),
            RemoteSubmitPrefix=submit_prefix, # Actually send jobs
            short_message=short_message
        )

    except:
        exception_message = str(sys.exc_info()[0]) + '\n' + str(
            sys.exc_info()[1]) + '\n' + str(sys.exc_info()[2])
        post_to_slack(
            'Switching off. {0},  something went wrong while scanning '
            'the event (python caught an exception): ```{1}``` *I blame human error*'.format(shifters_slackid,
exception_message))
        raise  # re-raise exceptions


if __name__ == "__main__":

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()

    parser.add_argument("-x", "--execute",
                      action="store_true", dest="execute", default=False,
                      help="Send scans to cluster")
    parser.add_argument("-l", "--localhost",
                      action="store_true", dest="localhost", default=False,
                      help="Listen to localhost for alerts")
    parser.add_argument("-t", "--tmux_spawn",
                      action="store_true", dest="tmuxspawn", default=False,
                      help="Spawn new jobs with tmux")
    parser.add_argument("-s", "--slackchannel",
                      dest="slackchannel", default="#gfu_live",
                      help="Slack channel")
    parser.add_argument("-n", "--nworkers",
                      dest="nworkers", default=1000,
                      help="Number of workers to send out")
    parser.add_argument( "--event", dest="event", default=None,
                      help="Send scans to cluster")

    args = parser.parse_args()

    config.slack_channel = args.slackchannel
    distribute_numclients = args.nworkers
    # If execute is not toggled on, then replace perform_scan with dummy
    # function

    if not args.execute:

        def perform_scan(**kwargs):
            post_to_slack("Scanning Mode is disabled! No scan will be "
                          "performed.")
            return {}

    # If localhost is toggled, listen for local replays

    if args.localhost:
        # ==============================================================================
        # Configure whether to listen to localhost stream. Default is live stream
        # ==============================================================================
        realtime_tools.config.ZMQ_HOST = 'localhost'
        realtime_tools.config.ZMQ_SUB_PORT = 5556
        final_channels = [args.slackchannel]
        # If untoggled, you can replay alerts using commands such as:
        # python $I3_SRC/realtime_tools/resources/scripts/replayI3LiveMoni.py --varname=realtimeEventData --pass=skua --start="2019-02-14 16:09:00" --stop="2019-02-14 16:15:39"
    
    if realtime_tools.config.ZMQ_HOST == 'live.icecube.wisc.edu':
        notify_alert = "<!channel> I have found a `{0}` `{1}` Alert." \
                       "I will scan this."
        final_channels = [args.slackchannel] # "#alerts"

    # The alert listener can spawn new alert listeners. If a specific path is given, the listener 
    # will open that pickle file and read the message inside. Otherwise will proceed as normal. 
    if args.event is not None:
        with open(args.event, "rb") as f:
            event = Pickle.load(f)
        individual_event(event)
        os.remove(args.event)

    else:

        # Post initial message to verify Slack connection

        post_to_slack("Switching on. I will now listen to the stream from `{0}`. "
                      "Sending scans is toggled to `{1}`. "
                      "".format(realtime_tools.config.ZMQ_HOST, args.execute))

        # Replace default behaviour with script to spawn new tmux sessions for each event

        if args.tmuxspawn:
            def incoming_event(varname, topics, event):
                """
                Handle incoming events and perform a full scan.
                """
                uid = str(hash(event["time"]))
                event_path = event_cache_dir + uid + ".pkl"
                env_path = os.getenv('I3_BUILD')
                with open(event_path, "wb") as f:
                    Pickle.dump(event, f)
                cmd = "bash " + submit_file + " " + uid + " " + env_path + ' " --event ' + event_path
                cmd += " -n " + str(args.nworkers) + " -s '" + args.slackchannel + "'"
                if args.execute:
                     cmd += " -x "
                if args.localhost:
                     cmd += " -l "
                cmd += '"'
                os.system(cmd)

        # create the daemon functionality

        try:
 
            realtime_tools.make_receiver(

                varname='realtimeEventData',
                topic=['HESE', 'EHE', 'ESTRES', 'realtimeEventData', 'neutrino'],
                callback=incoming_event
            )

        except:
            exception_message = str(sys.exc_info()[0]) + '\n' + str(
                sys.exc_info()[1]) + '\n' + str(sys.exc_info()[2])
            post_to_slack(
                'Switching off. {0},  something went wrong with the '
                'listener (python caught an exception): ```{1}``` *I blame human error*'.format(shifters_slackid,
                    exception_message))
            raise
