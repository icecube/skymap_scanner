import os
import logging
import argparse

from icecube import realtime_tools

from alert_listener.config import source_stream, stream_topics, shifters_slackid
from alert_listener.cache_manager import CacheManager
from alert_listener.event_handling import EventHandler

from alert_listener.slack_tools import SlackInterface
from alert_listener.slack_tools import MessageHelper as msg

if __name__ == "__main__":

    # ========
    # LOGGING
    # ========

    log = logging.getLogger(__name__)

    log.setLevel(logging.INFO)

    # ================
    # ARGUMENT PARSER
    # ================

    parser = argparse.ArgumentParser(description="New Alert Daemon")

    parser.add_argument(
        "-x",
        "--execute",
        action="store_true",
        dest="execute",
        default=False,
        help="Send scans to cluster",
    )
    parser.add_argument(
        "-l",
        "--localhost",
        action="store_true",
        dest="localhost",
        default=False,
        help="Listen to localhost for alerts",
    )
    parser.add_argument(
        "-s", "--slackchannel", dest="slackchannel", default=None, help="Slack channel"
    )
    parser.add_argument(
        "-k", "--slackkey", dest="slackkey", default=None, help="Slack key file"
    )
    parser.add_argument(
        "-n",
        "--nworkers",
        dest="nworkers",
        default=1000,
        help="Number of workers to send out",
    )

    args = parser.parse_args()

    # ================
    # SLACK INTERFACE
    # ================

    # TODO: better handling of case args.slackchannel = None
    slack = SlackInterface(
        whoami="New Alert Daemon", channel=args.slackchannel, api_keyfile=args.slackkey
    )

    # ================
    # MAIN LOGIC
    # ================

    if args.localhost:
        log.info("Listening to localhost for alerts")
        # overwriting config variables on an external module is not the best design, but that is how `make_receiver` works
        # see issue https://github.com/icecube/realtime/issues/6
        realtime_tools.config.ZMQ_HOST = "localhost"
        realtime_tools.config.ZMQ_SUB_PORT = 5556

    slack.post(msg.switch_on(realtime_tools.config.ZMQ_HOST, args.execute))

    cache_manager = CacheManager()

    event_handler = EventHandler(cache_manager=cache_manager)

    try:
        realtime_tools.make_receiver(
            varname=source_stream, topic=stream_topics, callback=event_handler
        )
    except Exception as err:
        exception_message = (
            f"Type: {type(err)} - Message: {err} -  Traceback: {err.__traceback__}"
        )
        slack.post(msg.switch_off(shifters_slackid, exception_message))
        raise err
