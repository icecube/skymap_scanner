"""Alert listener."""

# fmt: off
# pylint: skip-file

import datetime
import logging
import os
import pickle as Pickle
import random
import shutil
import subprocess
import sys

import numpy as np
from icecube import dataio, realtime_tools

from .. import config, extract_json_message
from . import create_plot, get_best_fit_v2, loop_over_plots, slack_tools
from .scan_logic import extract_short_message, stream_logic_map, whether_to_scan

# ==============================================================================
# Configure whether to listen to localhost stream. Default is live stream
# ==============================================================================

# If you want to listen to replayed events, uncomment the following two lines:
# realtime_tools.config.ZMQ_HOST = 'localhost'
# realtime_tools.config.ZMQ_SUB_PORT = 5556

# If untoggled, you can replay alerts using commands such as:

# python $I3_SRC/realtime_tools/resources/scripts/replayI3LiveMoni.py --varname=realtimeEventData --pass=skua --start="2019-02-14 16:09:00" --stop="2019-02-14 16:15:39"


# ==============================================================================
# Set the rate of GFU prescaling.
# ==============================================================================

# For GFU-only events, only 1 in N are sent out to slack
gfu_prescale = 40.

# ==============================================================================
# Configure Slack posting settings
# ==============================================================================


def post_to_slack(text):
    # never crash because of Slack
    try:
        logger = logging.getLogger()
        logger.info(text)
        return slack_tools.post_message(text)
    except:
        pass


# If archival alerts are replayed, no @channel notification will be used.
# However, if live alerts are found, the slack channel will be notified.

if realtime_tools.config.ZMQ_HOST == 'live.icecube.wisc.edu':
    notify_alert = "<!channel> I have found a `{0}` `{1}` Alert." \
                   "I will scan this."
#    notify_alert = "<@U64169Z6C> I have found a `{0}` `{1}` Alert. " \
#                   "I will scan this."
notify_alert = "<@UQ8LZG42G> I have found a `{0}` `{1}` Alert. I will scan this."

# If opertaing on cobalt machines, ssh into submitter
# Otherise, submit from the followup machines directly
if realtime_tools.config.NAME == "PRIVATE":
    submit_prefix = "ssh submitter"
else:
    submit_prefix = ""

# ==============================================================================
# Configure paths and ports for downloading/scanning
# ==============================================================================

event_cache_dir = os.path.join(realtime_tools.config.SCRATCH, "skymap_scanner_cache/")

try:
    os.makedirs(event_cache_dir)
except OSError:
    pass

# Hardcode path to GCD file on cvmfs

#gcd_dir = os.path.join("/cvmfs/icecube.opensciencegrid.org/users/steinrob/GCD/PoleBaseGCDs/baseline_gcd_131577.i3")
gcd_dir = "/cvmfs/icecube.opensciencegrid.org/users/RealTime/GCD/PoleBaseGCDs/"
# distribute_port = "21339"
distribute_numclients = 1000.

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


def spawn_scan(
    event_pkl,
    # post_to_slack,
    # event_id_string,
    # state_dict,
    cache_dir,
    # port,
    # numclients,
    # logger,  # logging callback
    # skymap_plotting_callback,
    # RemoteSubmitPrefix,  # Actually send jobs
    # short_message,
    gcd_dir,
    skymap_scanner_server_broker,  # for pulsar
    skymap_scanner_server_broker_auth,  # for pulsar
    skymap_scanner_server_log_level,  # for server
):

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
    # state_dict = perform_scan(finish_function=finish_function, **kwargs)
    subprocess.check_call(
        (
            f"python -m server "
            f"--cache-dir {event_cache_dir} "
            f"--event-pkl {event_pkl} "
            f"--broker {skymap_scanner_server_broker} "
            f"--auth-token {skymap_scanner_server_broker_auth} "
            f"--log {skymap_scanner_server_log_level} "
        ).split()
    )


# ==============================================================================
# Function to run on each incoming alert
# ==============================================================================
def incoming_event(varname, topics, event):
    individual_event(event)

def individual_event(
    event,
    event_pkl,
    skymap_scanner_server_broker,  # for pulsar
    skymap_scanner_server_broker_auth,  # for pulsar
    skymap_scanner_server_log_level,  # for server
):

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
        # NOTE - JSON extraction logic is duplicated in skymap_scanner.server
        # FIXME - decide if we can live without extracting this here as well (okay either way)
        event_id, state_dict = extract_json_message.extract_json_message(
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
            event_pkl=event_pkl,
            # post_to_slack,
            # event_id_string=event_id,
            # state_dict=state_dict,
            cache_dir=event_cache_dir,
            # port=port_number(),
            # numclients=distribute_numclients,
            # logger=post_to_slack,  # logging callback
            # skymap_plotting_callback=lambda d: skymap_plotting_callback(
            #     event_id, d),
            # RemoteSubmitPrefix=submit_prefix, # Actually send jobs
            # short_message=short_message
            gcd_dir=gcd_dir,
            skymap_scanner_server_broker=skymap_scanner_server_broker,
            skymap_scanner_server_broker_auth=skymap_scanner_server_broker_auth,
            skymap_scanner_server_log_level=skymap_scanner_server_log_level,
        )

    except:
        exception_message = str(sys.exc_info()[0]) + '\n' + str(
            sys.exc_info()[1]) + '\n' + str(sys.exc_info()[2])
        post_to_slack(
            'Switching off. <@UQ8LZG42G>,  something went wrong while scanning '
            'the event (python caught an exception): ```{0}``` *I blame human error*'.format(
                exception_message))
        raise  # re-raise exceptions


def main():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-x", "--execute",
                      action="store_true", dest="execute", default=False,
                      help="Send scans to cluster")
    parser.add_option("-l", "--localhost",
                      action="store_true", dest="localhost", default=False,
                      help="Send scans to cluster")
    parser.add_option("-t", "--tmux_spawn",
                      action="store_true", dest="tmuxspawn", default=False,
                      help="Spawn new jobs with tmux")
    parser.add_option("-s", "--slackchannel",
                      dest="slackchannel", default="#gfu_live",
                      help="Slack channel")
    parser.add_option("-n", "--nworkers",
                      dest="nworkers", default=1000,
                      help="Number of workers to send out")
    parser.add_option( "--event", dest="event_pkl", default=None,
                      help="Send scans to cluster")

    # Server args to pass along
    parser.add_option("--server-broker",
                      dest="skymap_scanner_server_broker",
                      help="Server's Pulsar broker address")
    parser.add_option("--server-broker-auth",
                      dest="skymap_scanner_server_broker_auth",
                      help="Server's Pulsar broker auth token")
    parser.add_option("--server-log-level",
                      dest="skymap_scanner_server_log_level",
                      help="Server's logging level")

    # get parsed args
    (options, args) = parser.parse_args()

    config.slack_channel = options.slackchannel
    distribute_numclients = options.nworkers
    # If execute is not toggled on, then replace perform_scan with dummy
    # function

    if not options.execute:

        def perform_scan(**kwargs):
            post_to_slack("Scanning Mode is disabled! No scan will be "
                          "performed.")
            return {}

    # If localhost is toggled, listen for local replays

    if options.localhost:
        realtime_tools.config.ZMQ_HOST = 'localhost'
        realtime_tools.config.ZMQ_SUB_PORT = 5556
        final_channels = [options.slackchannel]
    
    if realtime_tools.config.ZMQ_HOST == 'live.icecube.wisc.edu':
        notify_alert = "<!channel> I have found a `{0}` `{1}` Alert." \
                       "I will scan this."
        final_channels = [options.slackchannel] # "#alerts"

    # The alert listener can spawn new alert listeners. If a specific path is given, the listener 
    # will open that pickle file and read the message inside. Otherwise will proceed as normal. 
    if options.event_pkl is not None:
        with open(options.event_pkl, "rb") as f:
            event = Pickle.load(f)
        individual_event(
            event,
            options.event_pkl,
            options.skymap_scanner_server_broker,
            options.skymap_scanner_server_broker_auth,
            options.skymap_scanner_server_log_level,
        )
        os.remove(options.event_pkl)

    else:

        # Post initial message to verify Slack connection

        post_to_slack("Switching on. I will now listen to the stream from `{0}`. "
                      "Sending scans is toggled to `{1}`. "
                      "".format(realtime_tools.config.ZMQ_HOST, options.execute))

        # Replace default behaviour with script to spawn new tmux sessions for each event

        if options.tmuxspawn:
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
                cmd += " -n " + str(options.nworkers) + " -s '" + options.slackchannel + "'"
                if options.execute:
                     cmd += " -x "
                if options.localhost:
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
                'Switching off. <@UQ8LZG42G>,  something went wrong with the '
                'listener (python caught an exception): ```{0}``` *I blame human error*'.format(
                    exception_message))
            raise


if __name__ == "__main__":
    main()
