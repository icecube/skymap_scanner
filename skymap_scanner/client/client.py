"""The Client service."""

import argparse
import asyncio
import logging
import os
import pickle
import subprocess
import sys
import time
from typing import Any

import mqclient_pulsar as mq
from wipac_dev_tools import logging_tools

OUT = "out_msg.pkl"
IN = "in_msg.pkl"

LOGGER = logging.getLogger("skymap-scanner-client")


def inmsg_to_infile(in_msg: Any, debug_infile: str) -> str:
    """Write the msg to the `IN` file.

    Also, dump to a file for debugging (if not "").
    """
    with open(IN, "wb") as f:
        LOGGER.info(f"Pickle-dumping pixel to file: {str(in_msg)} @ {IN}")
        pickle.dump(in_msg, f)
    if debug_infile:  # for debugging
        with open(debug_infile, "wb") as f:
            LOGGER.info(f"Pickle-dumping pixel to file: {str(in_msg)} @ {debug_infile}")
            pickle.dump(in_msg, f)
    return IN


def outfile_to_outmsg(debug_outfile: str) -> Any:
    """Read the msg from the `OUT` file.

    Also, dump to a file for debugging (if not "").
    """
    with open(OUT, "rb") as f:
        out_msg = pickle.load(f)
        LOGGER.info(f"Pickle-loaded scan from file: {str(out_msg)} @ {OUT}")
    os.remove(OUT)
    if debug_outfile:  # for debugging
        with open(debug_outfile, "wb") as f:
            LOGGER.info(
                f"Pickle-dumping scan to file: {str(out_msg)} @ {debug_outfile}"
            )
            pickle.dump(out_msg, f)
    return out_msg


async def scan_pixel_distributed(
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
    debug_directory: str = "",
) -> None:
    """Communicate with server and outsource pixel scanning to subprocesses."""
    LOGGER.info("Making MQClient queue connections...")
    except_errors = False  # TODO - only false during debugging; make fail safe logic (on server end?)
    in_queue = mq.Queue(
        address=broker,
        name=topic_to_clients,
        auth_token=auth_token,
        except_errors=except_errors,
    )
    out_queue = mq.Queue(
        address=broker,
        name=topic_from_clients,
        auth_token=auth_token,
        except_errors=except_errors,
    )

    LOGGER.info("Getting pixels from server to scan then send back...")
    async with in_queue.open_sub() as sub, out_queue.open_pub() as pub:
        async for in_msg in sub:
            LOGGER.info(f"Got a pixel to scan: {str(in_msg)}")

            # debugging logic
            if debug_directory:
                debug_time = time.time()
                debug_infile = os.path.join(debug_directory, f"{debug_time}.in.pkl")
                debug_outfile = os.path.join(debug_directory, f"{debug_time}.out.pkl")
            else:
                debug_infile = ""
                debug_outfile = ""

            # write
            inmsg_to_infile(in_msg, debug_infile)

            # call & check outputs
            cmd = (
                f"python -m skymap_scanner.client.scan_pixel "
                f"--in-file {IN} "
                f"--out-file {OUT} "
                f"--log {logging.getLevelName(LOGGER.getEffectiveLevel())}"
            ).split()
            LOGGER.info(f"Executing: {cmd}")
            result = subprocess.run(cmd, capture_output=True, check=False, text=True)
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd)
            if not os.path.exists(OUT):
                LOGGER.error("Out file was not written for pixel")
                raise RuntimeError("Out file was not written for pixel")

            # get
            out_msg = outfile_to_outmsg(debug_outfile)

            # send
            LOGGER.info("Sending scan to server...")
            await pub.send(out_msg)

    LOGGER.info("Done scanning.")


def main() -> None:
    """Start up Client service."""

    def _create_dir(val: str) -> str:
        os.makedirs(val)
        return val

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
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default="WARNING",
        help="the output logging level for third-party loggers",
    )
    parser.add_argument(
        "--debug-directory",
        default="",
        type=_create_dir,
        help="a directory to write all the incoming/outgoing .pkl files "
        "(useful for debugging)",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        args.log,
        first_party_loggers=[LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # go!
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
            debug_directory=args.debug_directory,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
