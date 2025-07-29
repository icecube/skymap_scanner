"""A better version of the `wait -n` command."""

import argparse
import os
import signal
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(
        description="Supervise background processes and exit if any fail."
    )
    parser.add_argument(
        "--pids",
        nargs="+",
        type=int,
        required=True,
        help="List of background process PIDs to monitor.",
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        required=True,
        help="List of labels (must match number of PIDs).",
    )
    args = parser.parse_args()

    if len(args.pids) != len(args.labels):
        parser.error("Number of --pids and --labels must be the same.")
    return dict(zip(args.pids, args.labels))


def main():
    pidmap = parse_args()
    pids = set(pidmap.keys())

    while pids:
        time.sleep(10)
        print("Checking for exited processes...")

        for pid in list(pids):
            try:
                result = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                print(
                    f"WARNING: PID {pid} could not be waited on (already reaped?)",
                    file=sys.stderr,
                )
                pids.remove(pid)
                continue

            # is it done?
            if result[0] == 0:
                continue  # still running

            # it's done
            exit_code = os.WEXITSTATUS(result[1])
            label = pidmap[pid]
            print(f"Process {pid} ({label}) exited with {exit_code}")
            pids.remove(pid)

            # did it fail?
            if exit_code != 0:
                print(f"ERROR: {label} failed. Terminating others...")
                # kill others
                for other in pids:
                    try:
                        os.kill(other, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                time.sleep(10)
                sys.exit(1)
            else:
                print(f"Process {pid} ({label}) exited successfully.")

    # fall-through
    print("All components finished successfully")


if __name__ == "__main__":
    main()
