"""The Client service."""

import argparse
import asyncio
import logging
import os
import pickle
import subprocess

import coloredlogs  # type: ignore[import]
import mqclient_pulsar as mq

OUT = "out_msg.pkl"
IN = "in_msg.pkl"


async def scan_pixel_distributed(
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
) -> None:
    """Communicate with server and outsource pixel scanning to subprocesses."""
    logging.info("Making MQClient queue connections...")
    in_queue = mq.Queue(address=broker, name=topic_to_clients, auth_token=auth_token)
    out_queue = mq.Queue(address=broker, name=topic_from_clients, auth_token=auth_token)

    logging.info("Getting pixels from server to scan then send back...")
    async with in_queue.open_sub() as sub, out_queue.open_pub() as pub:
        async for in_msg in sub:
            logging.info(f"Got a pixel to scan: {str(in_msg)}")

            # write
            with open(IN, "wb") as f:
                logging.info(f"Pickle-dumping pixel to file: {str(in_msg)} @ {IN}")
                pickle.dump(in_msg, f)

            # call
            subprocess.check_call(
                f"python -m scanner.scan_pixel --in-file {IN} --out-file {OUT}".split()
            )
            if not os.path.exists(OUT):
                logging.error("Out file was not written for pixel")

            # get
            with open(OUT, "rb") as f:
                out_msg = pickle.load(f)
                logging.info(f"Pickle-loaded scan from file: {str(out_msg)} @ {OUT}")
            os.remove(OUT)

            # send
            logging.info("Sending scan to server...")
            await pub.send(out_msg)

    logging.info("Done scanning.")


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
        logging.warning(f"{arg}: {val}")

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
    logging.info("Done.")


if __name__ == "__main__":
    main()
