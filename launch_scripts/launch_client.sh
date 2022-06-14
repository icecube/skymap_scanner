#!/bin/sh

set -x

# Get & transform arguments that are files/dirs for docker-mounting
# yes, this is simpler than a bash-native solution
export ARGS="$*" # all of the arguments stuck together into a single string
DOCKER_PY_ARGS=$(python3 -c '
import os
py_args = os.getenv("ARGS")

def extract_opt(py_args, opt):
    before, after = py_args.split(f" {opt} ", 1)
    val, after = after.split(" ", 1)
    return f"{before} {after}", val

py_args, debug_dir = extract_opt(py_args, "--debug-directory")
py_args, gcd = extract_opt(py_args, "--gcd-dir")

py_args = (
    f"{py_args} "
    f"--debug-directory /local/{os.path.basename(debug_dir)} "
    f"--gcd-dir /local/gcd-dir"
)

dockermount_args = (
    f"--mount type=bind,source={debug_dir},target=/local/{os.path.basename(debug_dir)} "
    f"--mount type=bind,source={gcd},target=/local/gcd-dir,readonly "
)

print(f"{dockermount_args}#{py_args}")
')
DOCKERMOUNT_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $1}')"
PY_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $2}')"

# Run
docker run --network="host" --rm -i \
    --shm-size=6gb \
    $DOCKERMOUNT_ARGS \
    --env PY_COLORS=1 \
    $SKYSCAN_CONTAINER skymap_scanner.client \
    $PY_ARGS