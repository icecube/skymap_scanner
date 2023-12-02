"""The Client service."""

import argparse
import asyncio
import json
import logging
from pathlib import Path

import ewms_pilot
from wipac_dev_tools import argparse_tools, logging_tools

from .. import config as cfg

LOGGER = logging.getLogger("skyscan.client")


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
        help=(
            "The filepath to the JSON file to startup the client "
            "(has keys 'mq_basename', 'baseline_GCD_file', and 'GCDQp_packet')"
        ),
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

    # read startup.json
    with open(args.client_startup_json, "rb") as f:
        startup_json_dict = json.load(f)
    with open("GCDQp_packet.json", "w") as f:
        json.dump(startup_json_dict["GCDQp_packet"], f)

    # check if baseline GCD file is reachable
    if not Path(startup_json_dict["baseline_GCD_file"]).exists():
        raise FileNotFoundError(startup_json_dict["baseline_GCD_file"])

    cmd = (
        "python -m skymap_scanner.client.reco_icetray "
        " --in-pkl {{INFILE}}"  # no f-string b/c want to preserve '{{..}}'
        " --out-pkl {{OUTFILE}}"  # ^^^
        " --gcdqp-packet-json GCDQp_packet.json"
        f" --baseline-gcd-file {startup_json_dict['baseline_GCD_file']}"
    )

    # go!
    LOGGER.info(
        f"Starting up a Skymap Scanner client for event: {startup_json_dict['mq_basename']=}"
    )
    asyncio.run(
        ewms_pilot.consume_and_reply(
            cmd=cmd,
            broker_client=cfg.ENV.SKYSCAN_BROKER_CLIENT,
            broker_address=cfg.ENV.SKYSCAN_BROKER_ADDRESS,
            auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
            queue_incoming=f"to-clients-{startup_json_dict['mq_basename']}",
            queue_outgoing=f"from-clients-{startup_json_dict['mq_basename']}",
            ftype_to_subproc=".pkl",
            ftype_from_subproc=".pkl",
            timeout_incoming=cfg.ENV.SKYSCAN_MQ_TIMEOUT_TO_CLIENTS,
            timeout_outgoing=cfg.ENV.SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS,
            timeout_wait_for_first_message=cfg.ENV.SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE,
            debug_dir=args.debug_directory,
            task_timeout=cfg.ENV.EWMS_PILOT_TASK_TIMEOUT,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
