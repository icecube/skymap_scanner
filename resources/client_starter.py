"""An HTCondor script for spawning Skymap Scanner clients."""

# pylint:disable=no-member

import argparse
import datetime as dt
import getpass
import json
import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple

import coloredlogs  # type: ignore[import]
import htcondor  # type: ignore[import]
from rest_tools.client import RestClient


def get_schedd(collector_address: str, schedd_name: str) -> htcondor.Schedd:
    """Get object for talking with HTCondor schedd.

    Examples:
        `collector_address = "foo-bar.icecube.wisc.edu"`
        `schedd_name = "baz.icecube.wisc.edu"`
    """
    schedd_ad = htcondor.Collector(collector_address).locate(  # ~> exception
        htcondor.DaemonTypes.Schedd, schedd_name
    )
    schedd = htcondor.Schedd(schedd_ad)
    logging.info(f"Connected to Schedd {collector_address=} {schedd_name=}")
    return schedd


def make_condor_logs_subdir(directory: Path) -> Path:
    """Make the condor logs subdirectory."""
    iso_now = dt.datetime.now().isoformat(timespec="seconds")
    subdir = directory / f"skyscan-{iso_now}"
    subdir.mkdir(parents=True)
    logging.info(f"HTCondor will write log files to {subdir}")
    return subdir


def make_condor_job_description(  # pylint: disable=too-many-arguments
    logs_subdir: Path,
    # condor args
    memory: str,
    accounting_group: str,
    # skymap scanner args
    singularity_image: str,
    startup_json: Path,
    client_args: str,
) -> htcondor.Submit:
    """Make the condor job description object."""
    transfer_input_files: List[str] = [str(startup_json)]

    # NOTE:
    # In the newest version of condor we could use:
    #   universe = container
    #   container_image = ...
    #   arguments = python -m ...
    # But for now, we're stuck with:
    #   executable = ...
    #   +SingularityImage = ...
    #   arguments = /usr/local/icetray/env-shell.sh python -m ...
    # Because "this universe doesn't know how to do the
    #   entrypoint, and loading the icetray env file
    #   directly from cvmfs messes up the paths" -DS

    # write
    submit_dict = {
        "executable": "/bin/sh",
        "arguments": f"/usr/local/icetray/env-shell.sh python -m skymap_scanner.client {client_args} --startup-json-dir .",
        "+SingularityImage": singularity_image,
        "getenv": "SKYSCAN_*, EWMS_*, PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC",
        "output": str(logs_subdir / "client-$(ProcId).out"),
        "error": str(logs_subdir / "client-$(ProcId).err"),
        "log": str(logs_subdir / "client.log"),
        "+FileSystemDomain": "blah",
        "should_transfer_files": "YES",
        "transfer_input_files": ",".join(
            [os.path.abspath(f) for f in transfer_input_files]
        ),
        "request_cpus": "1",
        "request_memory": memory,
        "notification": "Error",
    }

    # accounting group
    if accounting_group:
        submit_dict["+AccountingGroup"] = f"{accounting_group}.{getpass.getuser()}"

    return htcondor.Submit(submit_dict)


def connect_to_skydriver() -> Tuple[Optional[RestClient], int]:
    """Connect to SkyDriver REST server, if the needed env vars are present.

    Also return the scan id.
    """
    address = os.getenv("SKYSCAN_SKYDRIVER_ADDRESS")
    if not address:
        logging.warning("Not connecting to SkyDriver")
        return None, -1

    scan_id = os.getenv("SKYSCAN_SKYDRIVER_SCAN_ID")
    if not scan_id:
        raise RuntimeError(
            "Cannot connect to SkyDriver without `SKYSCAN_SKYDRIVER_SCAN_ID`"
        )

    skydriver_rc = RestClient(address, token=os.getenv("SKYSCAN_SKYDRIVER_AUTH"))
    logging.info("Connected to SkyDriver")

    return skydriver_rc, int(scan_id)


def update_skydriver(
    skydriver_rc: RestClient,
    scan_id: int,
    submit_result: htcondor.SubmitResult,
) -> None:
    """Send SkyDriver updates from the `submit_result`."""
    skydriver_rc.request_seq(
        "PATCH",
        f"/scan/manifest/{scan_id}",
        {
            "condor_metadata": {
                "cluster_id": submit_result.cluster(),
                "jobs": submit_result.num_procs(),
                "cluster_ad": json.loads(submit_result.clusterad().printJson()),
            }
        },
    )


def main() -> None:
    """Prep and submit Condor job(s)."""
    parser = argparse.ArgumentParser(
        description=(
            "Submit Condor jobs running Skymap Scanner clients: "
            "Condor log files to {logs_directory}/skyscan-{datetime}."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def wait_for_file(waitee: Path, wait_time: int) -> Path:
        """Wait for `waitee` to exist, then return fullly-resolved path."""
        elapsed_time = 0
        sleep = 5
        while not waitee.exists():
            logging.info(f"waiting for {waitee} ({sleep}s intervals)...")
            time.sleep(sleep)
            elapsed_time += sleep
            if elapsed_time >= wait_time:
                raise argparse.ArgumentTypeError(
                    f"FileNotFoundError: waited {wait_time}s [{waitee}]"
                )
        return waitee.resolve()

    # helper args
    parser.add_argument(
        "--dryrun",
        default=False,
        action="store_true",
        help="does everything except submitting the condor job(s)",
    )
    parser.add_argument(
        "--logs-directory",
        required=True,
        type=Path,
        help="where to save logs",
    )
    parser.add_argument(
        "--collector-address",
        default=None,
        help="the full URL address of the HTCondor collector server. Ex: foo-bar.icecube.wisc.edu",
    )
    parser.add_argument(
        "--schedd-name",
        required=True,
        help="the full DNS name of the HTCondor Schedd server. Ex: baz.icecube.wisc.edu",
    )

    # condor args
    parser.add_argument(
        "--accounting-group",
        default="",
        help=(
            "the accounting group to use, ex: 1_week. "
            "By default no accounting group is used."
        ),
    )
    parser.add_argument(
        "--jobs",
        required=True,
        type=int,
        help="number of jobs",
        # default=4,
    )
    parser.add_argument(
        "--memory",
        required=True,
        help="amount of memory",
        # default="8GB",
    )

    # client args
    parser.add_argument(
        "--singularity-image",
        required=True,
        help="a path or url to the singularity image",
    )
    parser.add_argument(
        "--startup-json",
        help="The 'startup.json' file to startup each client",
        type=lambda x: wait_for_file(
            Path(x), int(os.getenv("CLIENT_STARTER_WAIT_FOR_STARTUP_JSON", "60"))
        ),
    )
    parser.add_argument(
        "--client-args",
        required=True,
        nargs="+",
        help="n 'key:value' pairs containing the python CL arguments to pass to skymap_scanner.client",
    )

    args = parser.parse_args()
    for arg, val in vars(args).items():
        logging.warning(f"{arg}: {val}")

    logs_subdir = make_condor_logs_subdir(args.logs_directory)

    # get client args
    client_args = ""
    for carg_value in args.client_args:
        carg, value = carg_value.split(":", maxsplit=1)
        client_args += f" --{carg} {value} "
    logging.info(f"Client Args: {client_args}")
    if "--startup-json-dir" in client_args:
        raise RuntimeError(
            "The '--client-args' file cannot include \"--startup-json-dir\". "
            "This needs to be defined explicitly with '--startup-json'."
        )

    # make condor job description
    job_description = make_condor_job_description(
        logs_subdir,
        # condor args
        args.memory,
        args.accounting_group,
        # skymap scanner args
        args.singularity_image,
        args.startup_json,
        client_args,
    )
    logging.info(job_description)

    # dryrun?
    if args.dryrun:
        logging.error("Script Aborted: Condor job not submitted")
        return

    # make connections -- do these before submitting so we don't have any unwanted surprises
    skydriver_rc, scan_id = connect_to_skydriver()
    schedd = get_schedd(args.collector_address, args.schedd_name)

    # submit
    submit_result = schedd.submit(job_description, count=args.jobs)  # submit N jobs
    logging.info(submit_result)

    # report to SkyDriver
    if skydriver_rc:
        update_skydriver(skydriver_rc, scan_id, submit_result)
        logging.warning("Sent cluster info to SkyDriver")


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")
    main()
