"""The Client service."""

import argparse
import asyncio
import json
import logging
from pathlib import Path

import ewms_pilot
from wipac_dev_tools import argparse_tools, logging_tools

from . import config as cfg

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
        "--startup-json-dir",
        help=(
            "The directory with the 'startup.json' file to startup the client "
            "(has keys 'mq_basename', 'baseline_GCD_file', and 'GCDQp_packet')"
        ),
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_dir(),
            NotADirectoryError(x),
        ),
    )

    # mq args
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The MQ broker URL to connect to",
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
    logging_tools.set_level(
        cfg.ENV.SKYSCAN_LOG,
        first_party_loggers=["skyscan", ewms_pilot.pilot.LOGGER],
        third_party_level=cfg.ENV.SKYSCAN_LOG_THIRD_PARTY,
        use_coloredlogs=True,
        future_third_parties=["google", "pika"],  # at most only one will be used
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # read startup.json
    with open(args.startup_json_dir / "startup.json", "rb") as f:
        startup_json_dict = json.load(f)
    with open("GCDQp_packet.json", "w") as f:
        json.dump(startup_json_dict["GCDQp_packet"], f)

    # check if baseline GCD file is reachable
    if not Path(startup_json_dict["baseline_GCD_file"]).exists():
        raise FileNotFoundError(startup_json_dict["baseline_GCD_file"])

    cmd = (
        f"python -m skymap_scanner.client.reco_icetray "
        f" --in-pkl in.pkl"
        f" --out-pkl out.pkl"
        f" --gcdqp-packet-json GCDQp_packet.json"
        f" --baseline-gcd-file {startup_json_dict['baseline_GCD_file']}"
    )

    # go!
    LOGGER.info(
        f"Starting up a Skymap Scanner client for event: {startup_json_dict['mq_basename']=}"
    )
    asyncio.run(
        ewms_pilot.consume_and_reply(
            cmd=cmd,
            broker_client="pulsar",
            broker_address=args.broker,
            auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
            queue_to_clients=f"to-clients-{startup_json_dict['mq_basename']}",
            queue_from_clients=f"from-clients-{startup_json_dict['mq_basename']}",
            timeout_to_clients=cfg.ENV.SKYSCAN_MQ_TIMEOUT_TO_CLIENTS,
            timeout_from_clients=cfg.ENV.SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS,
            debug_dir=args.debug_directory,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
