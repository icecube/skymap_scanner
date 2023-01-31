"""Make the Condor script for spawning Skymap Scanner clients."""

import argparse
import datetime as dt
import getpass
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import List

import coloredlogs  # type: ignore[import]
import htcondor  # type: ignore[import]


def get_schedd(collector_address: str, schedd_name: str) -> htcondor.Schedd:
    """Get object for talking with Condor schedd.

    Examples:
        `collector_address = "foo-bar.icecube.wisc.edu"`
        `schedd_name = "baz.icecube.wisc.edu"`
    """
    # pylint:disable=no-member
    schedd_ad = htcondor.Collector(collector_address).locate(  # ~> exception
        htcondor.DaemonTypes.Schedd, schedd_name
    )
    return htcondor.Schedd(schedd_ad)


def make_condor_scratch_dir() -> str:
    """Make the condor scratch directory."""
    scratch = os.path.join(
        "/scratch/",
        getpass.getuser(),
        f"skymap-scanner-{dt.datetime.now().isoformat(timespec='seconds')}",
    )
    os.makedirs(scratch)
    return scratch


def make_condor_file(  # pylint: disable=R0913,R0914
    # condor args
    scratch: str,
    jobs: int,
    memory: str,
    accounting_group: str,
    # skymap scanner args
    singularity_image: str,
    startup_json: Path,
    client_args: str,
) -> str:
    """Make the condor file."""
    condorpath = os.path.join(scratch, "condor")

    with open(condorpath, "w") as file:
        # accounting group
        accounting_group_attr = (
            f'+AccountingGroup="{accounting_group}.{getpass.getuser()}"'
            if accounting_group
            else ""
        )

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
        file.write(
            f"""executable = /bin/sh
arguments = /usr/local/icetray/env-shell.sh python -m skymap_scanner.client {client_args} --startup-json-dir .
+SingularityImage = "{singularity_image}"
getenv = SKYSCAN_*, EWMS_*, PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC
output = {scratch}/skymap_scanner.out
error = {scratch}/skymap_scanner.err
log = {scratch}/skymap_scanner.log
+FileSystemDomain = "blah"
should_transfer_files = YES
transfer_input_files = {",".join([os.path.abspath(f) for f in transfer_input_files])}
request_cpus = 1
{accounting_group_attr}
request_memory = {memory}
notification = Error
queue {jobs}
"""
        )

    return condorpath


def main() -> None:
    """Prep and execute Condor job.

    Make scratch directory and condor file.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Make Condor script for submitting Skymap Scanner clients: "
            "Condor log files in /scratch/{user}/skymap-scanner-{datetime}."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def wait_for_file(path: str, wait_time: int, subpath: str = "") -> Path:
        """Wait for `path` to exist, then return `Path` instance of `path`.

        If `subpath` is provided, wait for `"{path}/{subpath}"` instead.
        """
        if subpath:
            waitee = Path(path) / subpath
        else:
            waitee = Path(path)
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
        return Path(path).resolve()

    # condor args
    parser.add_argument(
        "--dryrun",
        default=False,
        action="store_true",
        help="does everything except submitting the condor job(s)",
    )
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
        type=lambda x: wait_for_file(x, 60 * 25),
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

    # make condor scratch directory
    scratch = make_condor_scratch_dir()

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

    # make condor file
    condorpath = make_condor_file(
        # condor args
        scratch,
        args.jobs,
        args.memory,
        args.accounting_group,
        # skymap scanner args
        args.singularity_image,
        args.startup_json,
        client_args,
    )

    # Execute
    if args.dryrun:
        logging.error(f"Script Aborted: Condor job not submitted ({condorpath}).")
    else:
        cmd = f"condor_submit {condorpath}"
        logging.info(cmd)
        subprocess.check_call(cmd.split(), cwd=scratch)


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")
    main()
