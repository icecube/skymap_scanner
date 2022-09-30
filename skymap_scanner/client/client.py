"""The Client service."""

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Optional

import ewms_pilot
from wipac_dev_tools import logging_tools

from .. import config as cfg

OUT_PKL = Path("out_msg.pkl")
IN_PKL = Path("in_msg.pkl")

LOGGER = logging.getLogger("skyscan-client")


def main() -> None:
    """Start up Client service."""

    def _create_dir(val: str) -> Optional[Path]:
        if not val:
            return None
        path = Path(val)
        path.mkdir(parents=True, exist_ok=True)
        return path

    parser = argparse.ArgumentParser(
        description=(
            "Start up client daemon to perform reco scans on pixels "
            "received from the server for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # "physics" args
    parser.add_argument(
        # we aren't going to use this arg, but just check if it exists for incoming pixels
        "-g",
        "--gcd-dir",
        default=cfg.DEFAULT_GCD_DIR,
        help="The GCD directory to use",
        type=Path,
    )
    parser.add_argument(
        "--gcdqp-packet-pkl",
        dest="GCDQp_packet_pkl",
        required=True,
        help="a pkl file containing the GCDQp_packet (list of I3Frames)",
        type=Path,
    )
    parser.add_argument(
        "--baseline-gcd-file",
        dest="baseline_GCD_file",
        required=True,
        help="the baseline_GCD_file string",
        type=str,
    )

    # mq args
    parser.add_argument(
        "--mq-basename",
        required=True,
        help="base identifier to correspond to an event for its MQ connections",
    )
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The MQ broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
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
        type=_create_dir,
        help="a directory to write all the incoming/outgoing .pkl files "
        "(useful for debugging)",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        args.log.upper(),
        first_party_loggers=[LOGGER, ewms_pilot.pilot.LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # check if Baseline GCD directory is reachable (also checks default value)
    if not Path(args.gcd_dir).is_dir():
        raise NotADirectoryError(args.gcd_dir)

    cmd = (
        f"python -m skymap_scanner.client.reco_pixel_pkl "
        f" --in-pkl {IN_PKL}"
        f" --out-pkl {OUT_PKL}"
        f" --gcdqp-packet-pkl {args.GCDQp_packet_pkl}"
        f" --baseline-gcd-file {args.baseline_GCD_file}"
        f" --log {args.log}"
        f" --log-third-party {args.log_third_party}"
    )

    # go!
    LOGGER.info(f"Starting up a Skymap Scanner client for event: {args.mq_basename=}")
    asyncio.get_event_loop().run_until_complete(
        ewms_pilot.consume_and_reply(
            cmd=cmd,
            broker_client=args.broker_client,
            broker_address=args.broker,
            auth_token=args.auth_token,
            queue_to_clients=f"to-clients-{args.mq_basename}",
            queue_from_clients=f"from-clients-{args.mq_basename}",
            timeout_to_clients=args.timeout_to_clients,
            timeout_from_clients=args.timeout_from_clients,
            debug_dir=args.debug_directory,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
