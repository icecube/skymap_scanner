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
    mq_basename: str,
    gcd_dir: str,
    broker: str,
    auth_token: str,
    log: str,
    log_third_party: str,
    timeout_to_clients: int,
    timeout_from_clients: int,
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
        executable = os.path.abspath("./scripts/launch_scripts/launch_client.sh")

        # write
        args = (
            f"--mq-basename {mq_basename} "
            f"--gcd-dir {gcd_dir} "
            f"--broker {broker} "
            f"--auth-token {auth_token} "
            f"--log {log} "
            f"--log-third-party {log_third_party} "
            f"--timeout-to-clients {timeout_to_clients} "
            f"--timeout-from-clients {timeout_from_clients}"
        )
        file.write(
            f"""executable = {executable}
arguments = {args}
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
    if not (
        os.getcwd().startswith(os.path.expanduser("~"))
        and os.getcwd().endswith("skymap_scanner")
        and "scripts" in os.listdir(".")
    ):
        raise RuntimeError(
            "You must run this script from home directory @ repo root (script uses relative paths)"
        )

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

    # skymap scanner args
    parser.add_argument(
        "--mq-basename",
        required=True,
        help="Skymap Scanner: base identifier to correspond to an event for its MQ connections",
    )
    parser.add_argument(
        "--gcd-dir",
        required=True,
        help="Skymap Scanner: the GCD directory to use",
    )
    parser.add_argument(
        "--broker",
        required=True,
        help="Skymap Scanner: the Pulsar broker URL to connect to",
    )
    parser.add_argument(
        "--auth-token",
        required=True,
        help="Skymap Scanner: the Pulsar authentication token to use",
    )
    parser.add_argument(
        "--timeout-to-clients",
        required=True,
        type=int,
        help="timeout (seconds) for messages TO client(s)",
    )
    parser.add_argument(
        "--timeout-from-clients",
        required=True,
        type=int,
        help="timeout (seconds) for messages FROM client(s)",
    )
    parser.add_argument(
        "-l",
        "--log",
        required=True,
        help="Skymap Scanner: the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        required=True,
        help="Skymap Scanner: the output logging level for third-party loggers",
    )

    args = parser.parse_args()
    for arg, val in vars(args).items():
        logging.warning(f"{arg}: {val}")

    # make condor scratch directory
    scratch = make_condor_scratch_dir()

    # make condor file
    condorpath = make_condor_file(
        # condor args
        scratch,
        args.jobs,
        args.memory,
        args.accounting_group,
        # skymap scanner args
        args.mq_basename,
        args.gcd_dir,
        args.broker,
        args.auth_token,
        args.log,
        args.log_third_party,
        args.timeout_to_clients,
        args.timeout_from_clients,
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
