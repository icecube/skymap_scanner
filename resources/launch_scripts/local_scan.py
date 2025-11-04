"""Runs a scanner instance (server & workers) all on the same machine."""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import TypeAlias

TAIL = int(os.getenv("CI_LOCAL_SCAN_TAIL", 5))
ProcessTuple: TypeAlias = tuple[str, subprocess.Popen, Path]


def _print_now(string: str) -> None:
    """Print immediately, prefixed with the date/time."""
    dt_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{dt_string} {string}", flush=True)

    # special github messages should be printed verbatim
    if any(string.startswith(x) for x in ["::error", "::warning", "::notice"]):
        print(string, flush=True)


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run a scanner instance (server and workers) on the same machine."
    )
    parser.add_argument(
        "n_workers",
        type=int,
        help="Number of workers to launch",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Output directory",
    )
    return parser.parse_args()


def _terminate_all(processes: list[ProcessTuple]) -> None:
    """Terminate all processes and give them a moment to exit."""
    for _, p, _ in processes:
        p.terminate()
    time.sleep(10)


def validate_env_vars() -> None:
    """Ensure required env vars exist and their directories are created."""
    required = [
        "CI_SKYSCAN_CACHE_DIR",
        "CI_SKYSCAN_OUTPUT_DIR",
        "CI_SKYSCAN_DEBUG_DIR",
    ]
    for var in required:
        if not os.getenv(var):
            sys.exit(f"Missing required env var: {var}")
        Path(os.environ[var]).mkdir(parents=True, exist_ok=True)


def wait_for_file(path: Path, timeout: int = 60) -> None:
    """Block until a file exists or time out with an error."""
    for _ in range(timeout):
        if path.exists():
            return
        time.sleep(1)
    _print_now(
        f"::error::Timed out waiting for file: {path}. Look at central server's output."
    )
    sys.exit(1)


def launch_process(
    cmd,
    stdout_file: Path,
    stderr_file: Path,
    cwd: Path | None = None,
) -> subprocess.Popen:
    """Launch a subprocess with optional stdout redirection and cwd."""
    _print_now(f"Launching process: {cmd}")
    return subprocess.Popen(
        cmd,
        stdout=open(stdout_file, "w"),
        stderr=(
            subprocess.STDOUT if stderr_file == stdout_file else open(stderr_file, "w")
        ),
        cwd=cwd,
    )


def build_server_cmd(outdir: Path, startup_json: Path) -> list[str]:
    """Build the command used to launch the server (Docker or Apptainer)."""
    threshold = os.getenv("_PREDICTIVE_SCANNING_THRESHOLD")
    predictive = ["--predictive-scanning-threshold", threshold] if threshold else []

    if os.environ["_SCANNER_CONTAINER_PLATFORM"] == "apptainer":
        if not os.environ["_SCANNER_IMAGE_APPTAINER"]:
            raise RuntimeError(
                "env var '_SCANNER_IMAGE_APPTAINER' must be set when '_SCANNER_CONTAINER_PLATFORM=apptainer'"
            )
        os.environ["SKYSCAN_EWMS_JSON"] = os.environ["_EWMS_JSON_ON_HOST"]  # forward
        return [
            "singularity",
            "run",
            os.environ["_SCANNER_IMAGE_APPTAINER"],
            #
            "python",
            "-u",  # unbuffered stdout/stderr
            "-m",
            "skymap_scanner.server",
            "--reco-algo",
            os.environ["_RECO_ALGO"],
            "--event-file",
            os.environ["_EVENTS_FILE"],
            "--cache-dir",
            os.environ["CI_SKYSCAN_CACHE_DIR"],
            "--output-dir",
            os.environ["CI_SKYSCAN_OUTPUT_DIR"],
            "--client-startup-json",
            str(startup_json),
            "--nsides",
            *os.environ["_NSIDES"].split(),
            "--simulated-event",
        ]
    elif os.environ["_SCANNER_CONTAINER_PLATFORM"] == "docker":
        env_flags: list[str] = []
        for key in os.environ:
            if key.startswith(("SKYSCAN_", "_SKYSCAN_", "EWMS_", "_EWMS_")):
                env_flags.extend(["--env", key])
        return [
            "docker",
            "run",
            f"--network={os.environ['_CI_DOCKER_NETWORK_FOR_DOCKER_IN_DOCKER']}",
            "--rm",
            #
            "--mount",
            f"type=bind,source={Path(os.environ['_EVENTS_FILE']).parent},target=/local/event,readonly",
            #
            "--mount",
            f"type=bind,source={os.environ['CI_SKYSCAN_CACHE_DIR']},target=/local/cache",
            #
            "--mount",
            f"type=bind,source={os.environ['CI_SKYSCAN_OUTPUT_DIR']},target=/local/output",
            #
            "--mount",
            f"type=bind,source={startup_json.parent},target=/local/startup",
            #
            "--mount",
            f"type=bind,source={Path(os.environ['_EWMS_JSON_ON_HOST']).parent},target=/local/ewms",
            #
            "--env",
            "PY_COLORS=1",
            #
            *env_flags,
            #
            "--env",
            f"SKYSCAN_EWMS_JSON=/local/ewms/{Path(os.environ['_EWMS_JSON_ON_HOST']).name}",
            #
            os.environ["_SCANNER_IMAGE_DOCKER"],
            #
            "python",
            "-u",  # unbuffered stdout/stderr
            "-m",
            "skymap_scanner.server",
            "--reco-algo",
            os.environ["_RECO_ALGO"],
            "--event-file",
            f"/local/event/{Path(os.environ['_EVENTS_FILE']).name}",
            "--cache-dir",
            "/local/cache",
            "--output-dir",
            "/local/output",
            "--client-startup-json",
            f"/local/startup/{startup_json.name}",
            "--nsides",
            *os.environ["_NSIDES"].split(),
            *predictive,
            "--real-event",
        ]
    else:
        raise RuntimeError(
            f"unknown '_SCANNER_CONTAINER_PLATFORM': {os.environ['_SCANNER_CONTAINER_PLATFORM']}"
        )


def _last_n_lines(fpath: Path, n: int) -> list[str]:
    """Return the last `n` lines of a file as a list of strings."""
    try:
        with open(fpath, "rb") as f:
            # Keep only last n lines in memory
            lines = deque(f, maxlen=n)
        return [line.rstrip(b"\n").decode() for line in lines]
    except Exception as e:
        return [f"<cannot get last lines: {e}>"]


def _validate_launch_dir() -> Path:
    """Ensure we are running from the expected directory and return it."""
    launch_dir = Path.cwd()
    if launch_dir.name != "launch_scripts":
        sys.exit("Script must be run from 'resources/launch_scripts' directory")
    return launch_dir


def _setup_startup_json(launch_dir: Path) -> Path:
    """Create startup.json path, ensure parent exists, and export its env var."""
    startup_json = launch_dir / "dir-for-startup-json" / "startup.json"
    startup_json.parent.mkdir(parents=True, exist_ok=True)
    os.environ["CI_SKYSCAN_STARTUP_JSON"] = str(startup_json)
    return startup_json


def _start_server(outdir: Path, startup_json: Path) -> ProcessTuple:
    """Start the central server process and return its tuple."""
    _print_now("Launching server...")
    server_cmd = build_server_cmd(outdir, startup_json)
    server_log = outdir / "server.out"
    server_proc = launch_process(
        server_cmd,
        stdout_file=server_log,
        stderr_file=server_log,
    )
    return ("central server", server_proc, server_log)


def _ensure_sysbox_for_docker_in_docker() -> None:
    """Ensure Sysbox is installed and active if we are using Docker-in-Docker."""
    if os.getenv("_SCANNER_CONTAINER_PLATFORM") != "docker":
        raise RuntimeError("sysbox is only required for docker -- don't run this check")

    # Check process running
    try:
        subprocess.run(["systemctl", "is-active", "--quiet", "sysbox"], check=True)
    except Exception:
        _print_now(
            "::error::Sysbox runtime is required for Docker-in-Docker but is not active."
        )
        _print_now(
            "Install via: https://github.com/nestybox/sysbox -- or see ewms-pilot docs for recommendations"
        )
        sys.exit(1)
    else:
        _print_now("Sysbox runtime (required for Docker-in-Docker) is active.")


def _start_workers(
    n_workers: int, launch_dir: Path, outdir: Path
) -> list[ProcessTuple]:
    """Start N worker processes and return their tuples."""
    if "EWMS_PILOT_TASK_TIMEOUT" not in os.environ:
        os.environ["EWMS_PILOT_TASK_TIMEOUT"] = str(30 * 60)  # 30 mins

    processes: list[ProcessTuple] = []
    _print_now(f"Launching {n_workers} workers...")
    for i in range(1, n_workers + 1):
        worker_dir = outdir / f"worker-{i}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = worker_dir / "pilot.out"
        stderr_path = worker_dir / "pilot.err"
        proc = launch_process(
            [str(launch_dir / "launch_worker.sh")],
            stdout_file=stdout_path,
            stderr_file=stderr_path,
            cwd=worker_dir,
        )
        processes.append((f"worker #{i}", proc, stdout_path))
        _print_now(f"\tworker #{i} launched")
    return processes


def _periodic_status(i: int, n_procs: int, og_n_procs: int) -> None:
    """Print periodic status header lines."""
    if i % 6 == 1:
        _print_now(f"{n_procs}/{og_n_procs} scan processes are running.")
    if i % 6 == 0:
        _print_now(
            f"checking in on all {n_procs}/{og_n_procs} running scan processes..."
        )
        _print_now("- - - - -")


def _maybe_tail(name: str, log: Path, i: int) -> None:
    """Tail the last N lines of a process log on schedule."""
    if i % 6 == 0:
        _print_now(f"{name} 'tail -{TAIL} {log}':")
        for ln in _last_n_lines(log, TAIL):
            _print_now(f"\t>>>\t{ln}")
        _print_now("- - - - -")


def _monitor_until_done(processes: list[ProcessTuple]) -> None:
    """Monitor processes, tail logs periodically, and handle failures."""
    og_len = len(processes)
    i = -1
    while processes:
        i += 1
        _periodic_status(i, len(processes), og_len)
        time.sleep(10)

        for name, proc, log in list(processes):
            ret = proc.poll()
            _maybe_tail(name, log, i)

            if ret is None:
                continue  # still running

            # it's done
            _print_now(f"Process {name} exited with code {ret}")
            processes.remove((name, proc, log))

            # did it fail?
            if ret != 0:
                _print_now(
                    f"::error::{name} failed. Terminating remaining processes..."
                )
                _terminate_all(processes)
                sys.exit(1)

    # fall-through
    _print_now("All components finished successfully")


def main() -> None:
    """Entry point for launching server and workers on the same machine."""
    processes: list[ProcessTuple] = []
    args = parse_args()

    if not os.getenv("_SCANNER_CONTAINER_PLATFORM"):
        raise RuntimeError("must provide env var '_SCANNER_CONTAINER_PLATFORM'")

    if os.environ["_SCANNER_CONTAINER_PLATFORM"] == "docker":
        _ensure_sysbox_for_docker_in_docker()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    validate_env_vars()

    launch_dir = _validate_launch_dir()
    startup_json = _setup_startup_json(launch_dir)

    # start server
    processes.append(_start_server(args.output_dir, startup_json))

    # wait for 'startup.json' file
    _print_now("Waiting for startup.json...")
    wait_for_file(startup_json)

    # start worker(s)
    processes.extend(_start_workers(args.n_workers, launch_dir, args.output_dir))

    _monitor_until_done(processes)


if __name__ == "__main__":
    main()
