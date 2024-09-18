"""The Client service."""

import argparse
import asyncio
import logging
from pathlib import Path

import ewms_pilot
from wipac_dev_tools import argparse_tools, logging_tools

from .. import config as cfg

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Start up Client service."""
    parser = argparse.ArgumentParser(
        description=(
            "Start up client daemon to perform reco scans on pixels "
            "received from the server for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # startup.json
    parser.add_argument(
        "--client-startup-json",
        help="The filepath to the JSON file with data needed to reco",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).parent.is_dir(),
            NotADirectoryError(Path(x).parent),
        ),
    )

    # testing/debugging args
    parser.add_argument(
        "--debug-directory",
        default="",
        type=argparse_tools.create_dir,
        help="a directory to write all the incoming/outgoing .pkl files "
        "(useful for debugging)",
    )

    args = parser.parse_args()
    cfg.configure_loggers()
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    cmd = (
        "python -m skymap_scanner.client.reco_icetray "
        " --in-pkl {{INFILE}}"  # no f-string b/c want to preserve '{{..}}'
        " --out-pkl {{OUTFILE}}"  # ^^^
        f" --client-startup-json {args.client_startup_json}"
    )

    # go!
    LOGGER.info(
        f"Starting up a Skymap Scanner client for scan: {cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID}"
    )
    LOGGER.info("Done.")
    asyncio.run(
        ewms_pilot.consume_and_reply(
            cmd=cmd,
            broker_client=cfg.ENV.SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE,  # was SKYSCAN_BROKER_CLIENT
            broker_address=cfg.ENV.SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS,  # was SKYSCAN_BROKER_ADDRESS
            auth_token=cfg.ENV.SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN,  # was SKYSCAN_BROKER_AUTH
            queue_incoming=cfg.ENV.SKYSCAN_MQ_TOCLIENT,
            queue_outgoing=cfg.ENV.SKYSCAN_MQ_FROMCLIENT,
            ftype_to_subproc=".pkl",
            ftype_from_subproc=".pkl",
            timeout_incoming=cfg.ENV.SKYSCAN_MQ_TIMEOUT_TO_CLIENTS,
            timeout_wait_for_first_message=cfg.ENV.SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE,
            debug_dir=args.debug_directory,
            task_timeout=cfg.ENV.EWMS_PILOT_TASK_TIMEOUT,
        )
    )
