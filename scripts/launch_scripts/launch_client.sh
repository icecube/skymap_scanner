#!/bin/bash

########################################################################
#
# Launch a Skymap Scanner client
#
# Pass in the arguments as if this were just the python script
#
########################################################################


# Get & transform arguments that are files/dirs for docker-mounting
# yes, this is simpler than a bash-native solution
export ARGS="$*" # all of the arguments stuck together into a single string
echo $ARGS
DOCKER_PY_ARGS=$(python3 -c '
import os
py_args = os.getenv("ARGS")

def extract_opt(py_args, opt):
    if opt not in py_args:
        return py_args, ""
    before, after = py_args.split(opt, 1)
    before, after = before.strip(), after.strip()
    if " " in after:
        val, after = after.split(" ", 1)
    else:  # for arg at end of string
        val, after = after, ""
    return f"{before} {after}", val

py_args, debug_dir = extract_opt(py_args, "--debug-directory")
py_args, gcd = extract_opt(py_args, "--gcd-dir")

dockermount_args = ""
py_args += " "

if debug_dir:
    dockermount_args += f"--mount type=bind,source={debug_dir},target=/local/debug "
    py_args += f"--debug-directory /local/debug "
if gcd:
    dockermount_args += f"--mount type=bind,source={gcd},target=/local/gcd,readonly "
    py_args += f"--gcd-dir /local/gcd "

print(f"{dockermount_args}#{py_args}")
')
DOCKERMOUNT_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $1}')"
PY_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $2}')"


set -x


# Toggle Options
PULL_POLICY="--pull=always"
if [ "$CI_TESTING_USE_LOCAL_DOCKER" == "1" ]; then
    PULL_POLICY=""
fi


# Run
docker run --network="host" $PULL_POLICY --rm -i \
    --shm-size=6gb \
    $DOCKERMOUNT_ARGS \
    --env PY_COLORS=1 \
    --env "PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=${PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC:=900}" \
    icecube/skymap_scanner:latest \
    python -m skymap_scanner.client \
    $PY_ARGS