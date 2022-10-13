"""Make the Condor script for spawning Skymap Scanner clients."""

import argparse
import datetime as dt
import getpass
import logging
import os
import subprocess
from typing import List

import coloredlogs  # type: ignore[import]


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

        transfer_input_files: List[str] = []

        # write
        file.write(
            f"""executable = python -m skymap_scanner.client
arguments = {client_args}
+SingularityImage = "{singularity_image}"
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
        # TODO - put default as CVMFS path, once that exists
        help="a path or url to the singularity image",
    )
    parser.add_argument(
        "--client-args-file",
        required=True,
        help="a text file containing the python CL arguments to pass to skymap_scanner.client",
    )

    args = parser.parse_args()
    for arg, val in vars(args).items():
        logging.warning(f"{arg}: {val}")

    # make condor scratch directory
    scratch = make_condor_scratch_dir()

    with open(args.client_args_file) as f:
        client_args = f.read()
        logging.info(f"Client Args: {client_args}")

    # make condor file
    condorpath = make_condor_file(
        # condor args
        scratch,
        args.jobs,
        args.memory,
        args.accounting_group,
        # skymap scanner args
        args.singularity_image,
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
