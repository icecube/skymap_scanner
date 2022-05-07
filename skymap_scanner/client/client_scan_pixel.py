"""The Client service."""

import argparse
import asyncio
import logging
import os
import subprocess

import coloredlogs  # type: ignore[import]
import mqclient_pulsar as mq

OUT = "out_msg"
IN = "in_msg"


async def scan_pixel_distributed(
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
) -> None:
    """Communicate with server and outsource pixel scanning to subprocesses."""
    in_queue = mq.Queue(address=broker, name=topic_to_clients, auth_token=auth_token)
    out_queue = mq.Queue(address=broker, name=topic_from_clients, auth_token=auth_token)

    async with in_queue.open_sub() as sub, out_queue.open_pub() as pub:
        async for in_msg in sub:
            with open(IN, "w") as f:
                f.write(in_msg)
            subprocess.check_call(
                f"python -m scanner.scan_pixel --in-file {IN} --out-file {OUT}".split()
            )
            if not os.path.exists(OUT):
                logging.error("Out file was not written for pixel")
            with open(OUT, "r") as f:
                out_msg = f.read()
            os.remove(OUT)
            await pub.send(out_msg)


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
                args.topics_root, f"to-clients-{args.event_name.replace('/', '-')}"
            ),
            topic_from_clients=os.path.join(
                args.topics_root, f"from-clients-{args.event_id.replace('/', '-')}"
            ),
        )
    )


if __name__ == "__main__":
    main()
