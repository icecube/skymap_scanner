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

from icecube.skymap_scanner.utils import create_event_id
from icecube.skymap_scanner.scan_logic import whether_to_scan, stream_logic_map, extract_short_message



# from icecube.skymap_scanner import slack_tools
# slack_tools is now tentatively symlinked to local directory
from slack_tools import SlackInterface
from slack_tools import MessageHelper as msg

slack = SlackInterface()

from listener_conf import gfu_prescale, gcd_dir, shifters_slackid

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
    slack.post(msg.intermediate_scan(event_id))

    # create a plot when done and upload it to slack
    plot_png_buffer = create_plot(event_id, state_dict)

    # we have a buffer containing a valid png file now, post it to Slack
    slack.upload_file(plot_png_buffer, "skymap_{0}.png".format(event_id),
                            "Skymap of {0}".format(event_id))


def spawn_scan(slack_interface, short_message=None, **kwargs):

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
        #slack_interface.post("Ra: {0}, Dec: {1}, Rad: {2}".format(ra, dec, rad))

        event_id = kwargs["event_id_string"]

        slack_interface.post(msg.scanning_done(event_id))

        def upload_func(png_buffer, filename, title):
            slack_interface.upload_file(png_buffer, filename, title)
        
        def log_func(text):
            slack_interface.post(text)
         
        loop_over_plots(event_id, state_dict=state_dict, cache_dir=event_cache_dir, ra=ra, dec=dec, radius=rad, log_func=log_func, upload_func=upload_func)
        
        try:
            get_best_fit_v2(event_id, cache_dir=event_cache_dir, log_func=log_func)
        except:
            pass

        slack_interface.post(msg.finish_message(event_id, event_cache_dir))

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
            slack.post(msg.nokey_value())
            return
        if "streams" not in event["value"]:
            slack.post(msg.nokey_streams())

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
            slack.post(msg.new_event(run, evt, alert_streams))

        # Post a Slack message for a random subset of GFU-only events

        elif (random.random() * gfu_prescale) < 1.:
            slack.post(msg.new_gfu(run, evt, frac=1./gfu_prescale))

        # try to get the event time
        p_frame = state_dict['GCDQp_packet'][-1]
        if "I3EventHeader" not in p_frame:
            slack.post(msg.missing_header(event_id))

        # Determine whether event should be scanned or not

        do_scan = whether_to_scan(p_frame, alert_streams, notify_alert,
                                  slack, short_message)

        # If event should not be scanned, do not scan. Post a message to
        # slack, unless the event is GFU-only

        if not do_scan:

            # Only notify if event is not GFU-only

            if alert_streams != ["neutrino"]:
                slack.post(msg.sub_threshold())

            # Delete file (which can be ~40Mb each!!!)

            shutil.rmtree(os.path.join(event_cache_dir, event_id))

            return # do not scan

        try:
            for f in stream_logic_map.values():
                if short_message is None:
                    short_message = f(extract_short_message(p_frame, slack))
        except:
            pass

        spawn_scan(
            slack,
            event_id_string=event_id,
            state_dict=state_dict,
            cache_dir=event_cache_dir,
            port=port_number(),
            numclients=distribute_numclients,
            # logger=post_to_slack,  # logging callback ??? TODO
            skymap_plotting_callback=lambda d: skymap_plotting_callback(
                event_id, d),
            RemoteSubmitPrefix=submit_prefix, # Actually send jobs
            short_message=short_message
        )

    except:
        exception_message = str(sys.exc_info()[0]) + '\n' + str(
            sys.exc_info()[1]) + '\n' + str(sys.exc_info()[2])
        slack.post(msg.scan_fail(shifters_slackid, exception_message))
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

    distribute_numclients = args.nworkers

    slack.set_channel(args.slackchannel)
    slack.set_api_key('./slack_api.key')

    # If execute is not toggled on, then replace perform_scan with dummy
    # function

    if not args.execute:

        def perform_scan(**kwargs):
            slack.post(msg.scan_disabled())
            return {}

    # If localhost is toggled, listen for local replays

    if args.localhost:
        # ==============================================================================
        # Configure whether to listen to localhost stream. Default is live stream
        # ==============================================================================
        realtime_tools.config.ZMQ_HOST = 'localhost'
        realtime_tools.config.ZMQ_SUB_PORT = 5556
        # If untoggled, you can replay alerts using commands such as:
        # python $I3_SRC/realtime_tools/resources/scripts/replayI3LiveMoni.py --varname=realtimeEventData --pass=skua --start="2019-02-14 16:09:00" --stop="2019-02-14 16:15:39"
    
    if realtime_tools.config.ZMQ_HOST == 'live.icecube.wisc.edu':
        notify_alert = "<!channel> I have found a `{0}` `{1}` Alert." \
                       "I will scan this."

    # The alert listener can spawn new alert listeners. If a specific path is given, the listener 
    # will open that pickle file and read the message inside. Otherwise will proceed as normal. 
    if args.event is not None:
        with open(args.event, "rb") as f:
            event = Pickle.load(f)
        individual_event(event)
        os.remove(args.event)

    else:

        # Post initial message to verify Slack connection

        slack.post(msg.switch_on(realtime_tools.config.ZMQ_HOST, args.execute))

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
            slack.post(msg.switch_off(shifters_slackid, exception_message))
            raise
