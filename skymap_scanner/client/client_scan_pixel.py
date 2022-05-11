"""The Client service."""

import argparse
import asyncio
import logging
import os
import pickle
import subprocess
import sys

import coloredlogs  # type: ignore[import]
import mqclient_pulsar as mq

OUT = "out_msg.pkl"
IN = "in_msg.pkl"

LOGGER = logging.getLogger("skymap-scanner-client")


async def scan_pixel_distributed(
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
) -> None:
    """Communicate with server and outsource pixel scanning to subprocesses."""
    LOGGER.info("Making MQClient queue connections...")
    in_queue = mq.Queue(address=broker, name=topic_to_clients, auth_token=auth_token)
    out_queue = mq.Queue(address=broker, name=topic_from_clients, auth_token=auth_token)

    LOGGER.info("Getting pixels from server to scan then send back...")
    async with in_queue.open_sub() as sub, out_queue.open_pub() as pub:
        async for in_msg in sub:
            LOGGER.info(f"Got a pixel to scan: {str(in_msg)}")

            # write
            with open(IN, "wb") as f:
                LOGGER.info(f"Pickle-dumping pixel to file: {str(in_msg)} @ {IN}")
                pickle.dump(in_msg, f)

            # call & check outputs
            cmd = f"python -m skymap_scanner.scanner.scan_pixel --in-file {IN} --out-file {OUT}".split()
            LOGGER.info(f"Executing: {cmd}")
            result = subprocess.run(cmd, capture_output=True, check=False)
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd)
            if not os.path.exists(OUT):
                LOGGER.error("Out file was not written for pixel")
                raise RuntimeError("Out file was not written for pixel")

            # get
            with open(OUT, "rb") as f:
                out_msg = pickle.load(f)
                LOGGER.info(f"Pickle-loaded scan from file: {str(out_msg)} @ {OUT}")
            os.remove(OUT)

            # send
            LOGGER.info("Sending scan to server...")
            await pub.send(out_msg)

    LOGGER.info("Done scanning.")


def main() -> None:
    """Start up Client service."""
    parser = argparse.ArgumentParser(
        description=(
            "Start up client daemon to perform millipede scans on pixels "
            "received from the server for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-e",
        "--event-name",
        required=True,
        help="Some identifier to correspond to an event for MQ connections",
    )
    parser.add_argument(
        "-t",
        "--topics-root",
        default="",
        help="A root/prefix to base topic names for communicating to/from client(s)",
    )
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The Pulsar broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
        help="The Pulsar authentication token to use",
    )
    parser.add_argument(
        "-l",
        "--log",
        default="INFO",
        help="the output logging level",
    )

    args = parser.parse_args()
    coloredlogs.install(level=args.log)
    for arg, val in vars(args).items():
        LOGGER.warning(f"{arg}: {val}")

    asyncio.get_event_loop().run_until_complete(
        scan_pixel_distributed(
            broker=args.broker,
            auth_token=args.auth_token,
            topic_to_clients=os.path.join(
                args.topics_root, f"to-clients-{os.path.basename(args.event_name)}"
            ),
            topic_from_clients=os.path.join(
                args.topics_root, f"from-clients-{os.path.basename(args.event_name)}"
            ),
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
