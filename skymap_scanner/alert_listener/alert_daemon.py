import os
import logging
import argparse

from icecube import realtime_tools

import config
from cache_manager import CacheManager
from event_handling import EventHandler

from slack_tools import SlackInterface
from slack_tools import MessageHelper as msg


def main():
    # ========
    # LOGGING
    # ========

    logging.basicConfig(level=logging.INFO)

    log = logging.getLogger(__name__)

    # ================
    # ARGUMENT PARSER
    # ================

    parser = init_parser()

    args = parser.parse_args()

    # ================
    # SLACK INTERFACE
    # ================

    # TODO: better handling of case args.slackchannel = None
    slack = SlackInterface(
        whoami="New Alert Daemon", channel=args.slackchannel, api_keyfile=args.slack_key
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

    msg_switchon = msg.switch_on(realtime_tools.config.ZMQ_HOST, args.process)

    log.info(msg_switchon), slack.post(msg_switchon)

    cache_manager = CacheManager()

    event_handler = EventHandler(cache_manager=cache_manager, process=args.process)

    try:
        realtime_tools.make_receiver(
            varname=config.source_stream,
            topic=config.stream_topics,
            callback=event_handler,
        )
    except Exception as err:
        exception_message = (
            f"Type: {type(err)} - Message: {err} -  Traceback: {err.__traceback__}"
        )
        slack.post(msg.switch_off(config.shifters_slackid, exception_message))
        raise err


def init_parser(description="New Alert Daemon"):

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "-p",
        "--process",
        action="store_true",
        dest="process",
        default=False,
        help="Call processor on incoming events",
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
        "-k", "--slack_key", dest="slack_key", default=None, help="Slack key file"
    )
    parser.add_argument(
        "-n",
        "--nworkers",
        dest="nworkers",
        default=1000,
        help="Number of workers to send out",
    )

    return parser


if __name__ == "__main__":
    main()
