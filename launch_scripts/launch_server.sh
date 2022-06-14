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

py_args, event = extract_opt(py_args, "--event-file")
py_args, cache = extract_opt(py_args, "--cache-dir")
py_args, gcd = extract_opt(py_args, "--gcd-dir")

py_args = f"{py_args} " \
       f"--event-file /local/event/{os.path.basename(event)} " \
       f"--cache-dir /local/{os.path.basename(cache)} " \
       f"--gcd-dir /local/gcd-dir"

dockermount_args = (
    f"--mount type=bind,source={os.path.dirname(event)},target=/local/event,readonly "
    f"--mount type=bind,source={cache},target=/local/{os.path.basename(cache)} "
    f"--mount type=bind,source={gcd},target=/local/gcd-dir,readonly "
)

print(f"{dockermount_args}#{py_args}")
')
DOCKERMOUNT_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $1}')"
PY_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $2}')"

echo $DOCKERMOUNT_ARGS
echo $PY_ARGS

# Run
docker run --network="host" --rm -i \
    $DOCKERMOUNT_ARGS \
    --env PY_COLORS=1 \
    $SKYSCAN_CONTAINER skymap_scanner.server \
    $PY_ARGS

    # --event-file /local/event/"$(basename $2)" \
    # --cache-dir /local/$SKYSCAN_CACHE_DIR \
    # --gcd-dir /local/gcd-dir \
    # --broker $PULSAR_ADDRESS \
    # --log DEBUG \
    # --mini-test-scan