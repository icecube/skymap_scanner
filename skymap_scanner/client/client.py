"""The Client service."""

import argparse
import asyncio
import json
import logging
from pathlib import Path

import ewms_pilot
from wipac_dev_tools import argparse_tools, logging_tools

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
    parser.add_argument(
        "-a",
        "--auth-token",
        default="",
        help="The MQ authentication token to use",
    )
    parser.add_argument(
        "--timeout-to-clients",
        default=60 * 1,
        type=int,
        help="timeout (seconds) for messages TO client(s)",
    )
    parser.add_argument(
        "--timeout-from-clients",
        default=60 * 30,
        type=int,
        help="timeout (seconds) for messages FROM client(s)",
    )

    # logging args
    parser.add_argument(
        "-l",
        "--log",
        default="INFO",
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default="WARNING",
        help="the output logging level for third-party loggers",
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
        args.log,
        first_party_loggers=["skyscan", ewms_pilot.pilot.LOGGER],
        third_party_level=args.log_third_party,
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
        raise FileNotFoundError(args.gcd_dir)

    cmd = (
        f"python -m skymap_scanner.client.reco_icetray "
        f" --in-pkl in.pkl"
        f" --out-pkl out.pkl"
        f" --gcdqp-packet-json GCDQp_packet.json"
        f" --baseline-gcd-file {startup_json_dict['baseline_GCD_file']}"
        f" --log {args.log}"
        f" --log-third-party {args.log_third_party}"
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
            auth_token=args.auth_token,
            queue_to_clients=f"to-clients-{startup_json_dict['mq_basename']}",
            queue_from_clients=f"from-clients-{startup_json_dict['mq_basename']}",
            timeout_to_clients=args.timeout_to_clients,
            timeout_from_clients=args.timeout_from_clients,
            debug_dir=args.debug_directory,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
