#!/usr/bin/env python

import os
import sys
import logging

from icecube import icetray, dataclasses, dataio, realtime_tools
from icecube.skymap_scanner import extract_json_message, perform_scan, create_plot
from icecube.skymap_scanner import slack_tools

def post_to_slack(text):
    # never crash because of Slack
    try:
        logger = logging.getLogger()
        logger.info(text)
        return slack_tools.post_message(text)
    except:
        pass

# enable this if you want to use realtime_tools/resources/scripts/publisher.py to send test messages
# a nice event can be replayed using this:
# python $I3_SRC/realtime_tools/resources/scripts/replayI3LiveMoni.py --varname=heseEvent16Data --pass=skua
realtime_tools.config.URL_ZMQ = 'tcp://localhost:5556'
event_cache_dir = os.path.join(os.environ["HOME"], "CK_experimental/skymaps/cache")
distribute_port = "11337"
distribute_numclients = 1000

def skymap_plotting_callback(event_id, state_dict):
    post_to_slack("I am creating a plot of the current status of the scan of `{0}` for you. This should only take a minute...".format(event_id))

    # create a plot when done and upload it to slack
    plot_png_buffer = create_plot(event_id, state_dict)
    
    # we have a buffer containing a valid png file now, post it to Slack
    slack_tools.upload_file(plot_png_buffer, "skymap_{0}.png".format(event_id), "Skymap of {0}".format(event_id))

def incoming_event(topic, event):
    """
    Handle incoming events and perform a full scan.
    """
    try:
        post_to_slack('I received a new "full event" message, its topic is `{0}`. I am extracting it now...'.format(topic))

        # get a file stager
        stagers = dataio.get_stagers()
        
        # extract the JSON message
        event_id, state_dict = extract_json_message(event, filestager=stagers, cache_dir=event_cache_dir)

        if 'baseline_GCD_file' in state_dict:
            post_to_slack('The event ID seems to be `{0}` and it uses a baseline GCD file named `{1}`.'.format(event_id, state_dict['baseline_GCD_file']))
        else:
            post_to_slack('The event ID seems to be `{0}` and no baseline GCD seems to be necessary.'.format(event_id))
        
        # try to get the event time
        p_frame = state_dict['GCDQp_packet'][-1]
        if "I3EventHeader" not in p_frame:
            post_to_slack("Something is wrong with this event (ID `{0}`). Its P-frame doesn't have a header... I will try to continue with submitting the scan anyway, but this doesn't look good.".format(event_id))
        else:
            time = p_frame["I3EventHeader"].start_time
            post_to_slack("Event `{0}` happened at `{1}`. I will now attempt to submit a full-sky millipede scan.".format(event_id, str(time)))
        
        # now perform the actual scan
        state_dict = perform_scan(
            event_id_string=event_id,
            state_dict=state_dict,
            cache_dir=event_cache_dir,
            port=distribute_port,
            numclients=distribute_numclients,
            logger=post_to_slack, # logging callback
            skymap_plotting_callback = lambda d: skymap_plotting_callback(event_id, d)
        )

        post_to_slack("Scanning of `{0}` is done. Let me create a plot for you real quick.".format(event_id))

        # create a plot when done and upload it to slack
        skymap_plotting_callback(event_id, state_dict)
        
        post_to_slack("Okay, that's it. I will be listening for new incoming events now.")
    except:
        exception_message = str(sys.exc_info()[0])+'\n'+str(sys.exc_info()[1])+'\n'+str(sys.exc_info()[2])
        post_to_slack('Something went wrong while scanning the event (python caught an exception): ```{0}```'.format(exception_message))
        raise # re-raise exceptions

# create the daemon functionality
realtime_tools.make_daemon(pidfile='HESE_scan_listener.pid',
                           logfile='HESE_scan_listener.log',
                           topics='heseEvent16Data',
                           callback=incoming_event)
