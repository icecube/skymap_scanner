#!/bin/bash

########################################################################
#
# Launch a Skymap Scanner client
#
# Pass in the arguments as if this were just the python sub-module
#
########################################################################


# Get & transform arguments that are files/dirs for docker-mounting
# yes, this is simpler than a bash-native solution
export ARGS="$*" # all of the arguments stuck together into a single string
echo $ARGS
DOCKER_PY_ARGS=$(python3 -c '
import os
py_args = os.getenv("ARGS")

def extract_opt_path(py_args, opt):
    if opt not in py_args:
        return py_args, None
    before, after = py_args.split(opt, 1)
    before, after = before.strip(), after.strip()
    if " " in after:
        val, after = after.split(" ", 1)
    else:  # for arg at end of string
        val, after = after, ""
    if val:
        return f"{before} {after}", os.path.abspath(val)
    return f"{before} {after}", None

py_args, debug_dir = extract_opt_path(py_args, "--debug-directory")
py_args, gcd = extract_opt_path(py_args, "--gcd-dir")
py_args, startup = extract_opt_path(py_args, "--client-startup-json")

dockermount_args = ""
py_args += " "

if debug_dir:
    dockermount_args += f"--mount type=bind,source={debug_dir},target=/local/debug "
    py_args += f"--debug-directory /local/debug "
if gcd:
    dockermount_args += f"--mount type=bind,source={gcd},target=/local/gcd,readonly "
    #
    # NOTE: WE ARE NOT FORWARDING THIS ARG TO THE SCRIPT B/C ITS PASSED WITHIN THE STARTUP.JSON
    #
if startup:
    dockermount_args += f"--mount type=bind,source={os.path.dirname(startup)},target=/local/startup "
    py_args += f"--client-startup-json /local/startup/{os.path.basename(startup)} "

print(f"{dockermount_args}#{py_args}")
')
DOCKERMOUNT_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $1}')"
PY_ARGS="$(echo $DOCKER_PY_ARGS | awk -F "#" '{print $2}')"


set -x


# Figure where to get image
# Figure pull policy
if [[ ${SKYSCAN_DOCKER_PULL_ALWAYS:-"1"} == "0" ]]; then
    pull_policy=""
else
    pull_policy="--pull=always"
fi


# Run
docker run --network="host" $pull_policy --rm -i \
    --shm-size=6gb \
    $DOCKERMOUNT_ARGS \
    --env PY_COLORS=1 \
    $(env | grep '^SKYSCAN_' | awk '$0="--env "$0') \
    $(env | grep '^EWMS_' | awk '$0="--env "$0') \
    $(env | grep '^RABBITMQ_' | awk '$0="--env "$0') \
    --env "RABBITMQ_HEARTBEAT=${RABBITMQ_HEARTBEAT:-600}" \
    $(env | grep '^PULSAR_' | awk '$0="--env "$0') \
    --env "PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=${PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC:-900}" \
    icecube/skymap_scanner:${SKYSCAN_DOCKER_IMAGE_TAG:-"latest"} \
    python -m skymap_scanner.client \
    $PY_ARGS