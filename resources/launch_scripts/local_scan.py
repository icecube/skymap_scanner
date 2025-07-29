"""Runs a scanner instance (server & workers) all on the same machine."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def parse_args():
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


def validate_env_vars():
    required = [
        "CI_SKYSCAN_CACHE_DIR",
        "CI_SKYSCAN_OUTPUT_DIR",
        "CI_SKYSCAN_DEBUG_DIR",
    ]
    for var in required:
        if not os.getenv(var):
            sys.exit(f"Missing required env var: {var}")
        Path(os.environ[var]).mkdir(parents=True, exist_ok=True)


def wait_for_file(path: Path, timeout: int = 60):
    for _ in range(timeout):
        if path.exists():
            return
        time.sleep(1)
    print(
        f"::error::Timed out waiting for file: {path}. Look at central server's output."
    )
    sys.exit(1)


def launch_process(cmd, stdout_file, cwd=None) -> subprocess.Popen:
    print(f"Launching process: {cmd}")
    return subprocess.Popen(
        cmd,
        stdout=open(stdout_file, "w") if stdout_file else subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        cwd=cwd,
    )


def build_server_cmd(outdir: Path, startup_json: Path) -> list[str]:
    threshold = os.getenv("_PREDICTIVE_SCANNING_THRESHOLD")
    if threshold:
        predictive = ["--predictive-scanning-threshold", threshold]
    else:
        predictive = []

    if os.getenv("_RUN_THIS_SIF_IMAGE"):
        os.environ["SKYSCAN_EWMS_JSON"] = os.environ["_EWMS_JSON_ON_HOST"]
        return [
            "singularity",
            "run",
            os.environ["_RUN_THIS_SIF_IMAGE"],
            #
            "python",
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
    else:
        env_flags = []
        for key in os.environ:
            if key.startswith(("SKYSCAN_", "_SKYSCAN_", "EWMS_", "_EWMS_")):
                env_flags.extend(["--env", key])
        return [
            "docker",
            "run",
            "--network=host",
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
            os.environ["CI_DOCKER_IMAGE_TAG"],
            #
            "python",
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


def main():
    processes: list[tuple[str, subprocess.Popen]] = []
    args = parse_args()

    # Validate directories
    args.output_dir.mkdir(parents=True, exist_ok=True)
    validate_env_vars()

    launch_dir = Path.cwd()
    if launch_dir.name != "launch_scripts":
        sys.exit("Script must be run from 'resources/launch_scripts' directory")

    # Setup startup JSON
    startup_json = launch_dir / "dir-for-startup-json" / "startup.json"
    startup_json.parent.mkdir(parents=True, exist_ok=True)
    os.environ["CI_SKYSCAN_STARTUP_JSON"] = str(startup_json)

    # Launch server
    print("Launching server...")
    server_cmd = build_server_cmd(args.output_dir, startup_json)
    server_log = args.output_dir / "server.out"
    server_proc = launch_process(server_cmd, stdout_file=server_log)
    processes.append(("server", server_proc))

    # Wait for startup.json
    print("Waiting for startup.json...")
    wait_for_file(startup_json)

    # Launch workers
    print(f"Launching {args.n_workers} workers...")
    os.environ["EWMS_PILOT_TASK_TIMEOUT"] = os.getenv("EWMS_PILOT_TASK_TIMEOUT", "1800")
    for i in range(1, args.n_workers + 1):
        worker_dir = args.output_dir / f"worker-{i}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        out_path = worker_dir / "pilot.out"
        proc = launch_process(
            [str(launch_dir / "launch_worker.sh")],
            stdout_file=out_path,
            cwd=worker_dir,
        )
        processes.append((f"worker #{i}", proc))
        print(f"\tworker #{i} launched")

    # Wait for all processes to finish
    while processes:
        time.sleep(10)
        for name, proc in list(processes):
            ret = proc.poll()

            # is it done?
            if ret is None:
                continue

            # it's done
            print(f"Process {name} exited with code {ret}")
            processes.remove((name, proc))

            # did it fail?
            if ret != 0:
                print(f"ERROR: {name} failed. Terminating remaining processes...")
                # terminate the others
                for _, p in processes:
                    p.terminate()
                time.sleep(10)
                sys.exit(1)

    # fall-through
    print("All components finished successfully")


if __name__ == "__main__":
    main()
