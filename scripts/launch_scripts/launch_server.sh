#!/bin/bash

########################################################################
#
# Launch the Skymap Scanner server
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

py_args, event = extract_opt_path(py_args, "--event-file")
py_args, cache = extract_opt_path(py_args, "--cache-dir")
py_args, output = extract_opt_path(py_args, "--output-dir")
py_args, gcd = extract_opt_path(py_args, "--gcd-dir")
py_args, startup = extract_opt_path(py_args, "--startup-files-dir")

dockermount_args = ""
py_args += " "

if event:
    dockermount_args += f"--mount type=bind,source={os.path.dirname(os.path.abspath(event))},target=/local/event,readonly "
    py_args += f"--event-file /local/event/{os.path.basename(event)} "
if cache:
    dockermount_args += f"--mount type=bind,source={os.path.abspath(cache)},target=/local/cache "
    py_args += f"--cache-dir /local/cache "
if output:
    dockermount_args += f"--mount type=bind,source={os.path.abspath(output)},target=/local/output "
    py_args += f"--output-dir /local/output "
if gcd:
    dockermount_args += f"--mount type=bind,source={os.path.abspath(gcd)},target=/local/gcd,readonly "
    py_args += f"--gcd-dir /local/gcd "
if startup:
    dockermount_args += f"--mount type=bind,source={os.path.abspath(startup)},target=/local/startup-files "
    py_args += f"--startup-files-dir /local/startup-files "

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
    $DOCKERMOUNT_ARGS \
    --env PY_COLORS=1 \
    $(env | grep '^SKYSCAN_' | awk '$0="--env "$0') \
    --env "PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=${PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC:=300}" \
    icecube/skymap_scanner:latest \
    python -m skymap_scanner.server \
    $PY_ARGS