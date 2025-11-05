#!/bin/bash
set -euo pipefail

########################################################################
#
# Launch a Skymap Scanner worker
#
# - Docker path: uses run_docker_in_docker.sh
# - Apptainer path: runs the pilot image that wraps Apptainer (no DIND)
#
########################################################################

# establish pilot's root path
tmp_rootdir="$(pwd)/pilot-$(uuidgen)"
mkdir "$tmp_rootdir"
cd "$tmp_rootdir"
export EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST="$tmp_rootdir"

# mark startup.json's dir to be bind-mounted into the task container (by the pilot)
# -> check that the dir only has one file, otherwise we may end up binding extra dirs
python -c 'import os; assert os.listdir(os.path.dirname(os.environ["CI_SKYSCAN_STARTUP_JSON"])) == ["startup.json"]'
export EWMS_PILOT_EXTERNAL_DIRECTORIES="$(dirname "$CI_SKYSCAN_STARTUP_JSON")"

# args
export EWMS_PILOT_TASK_ARGS="python -m skymap_scanner.client --infile {{INFILE}} --outfile {{OUTFILE}} --client-startup-json $CI_SKYSCAN_STARTUP_JSON"

# marshal SKYSCAN/_SKYSCAN_ env into JSON
json_var=$(env | grep -E '^(SKYSCAN_|_SKYSCAN_)' | awk -F= '{printf "\"%s\":\"%s\",", $1, $2}' | sed 's/,$//')
json_var="{$json_var}"
export EWMS_PILOT_TASK_ENV_JSON="$json_var"

# file types
export EWMS_PILOT_INFILE_EXT="JSON"
export EWMS_PILOT_OUTFILE_EXT="JSON"

# queues/broker config
export EWMS_PILOT_QUEUE_INCOMING=$(jq -r '.toclient.name' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN=$(jq -r '.toclient.auth_token' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE=$(jq -r '.toclient.broker_type' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS=$(jq -r '.toclient.broker_address' "$_EWMS_JSON_ON_HOST")

export EWMS_PILOT_QUEUE_OUTGOING=$(jq -r '.fromclient.name' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN=$(jq -r '.fromclient.auth_token' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE=$(jq -r '.fromclient.broker_type' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS=$(jq -r '.fromclient.broker_address' "$_EWMS_JSON_ON_HOST")


########################################################################
# Run!
########################################################################

# ─────────────── Case: Docker-in-Docker ───────────────
if [[ "${_CI_SCANNER_CONTAINER_PLATFORM}" == "docker" ]]; then

    # docker-specific pilot env vars
    export EWMS_PILOT_TASK_IMAGE="$_SCANNER_IMAGE_DOCKER"
    export _EWMS_PILOT_DOCKER_SHM_SIZE="6gb"  # CI-specific; prod infra should set this

    # Required env for the helper
    export DIND_OUTER_IMAGE="${_PILOT_IMAGE_FOR_DOCKER_IN_DOCKER}"
    export DIND_INNER_IMAGE="${_SCANNER_IMAGE_DOCKER}"
    # Network for the outer container
    export DIND_NETWORK="${_CI_DOCKER_NETWORK_FOR_DOCKER_IN_DOCKER}"
    # Bind dirs: the pilot needs these paths visible at the same locations
    # - tmp_rootdir (RW)
    # - startup.json's parent (RO)
    export DIND_BIND_RW_DIRS="$tmp_rootdir"
    export DIND_BIND_RO_DIRS="$(dirname "$CI_SKYSCAN_STARTUP_JSON")"
    # Forward envs by prefix and explicit list
    export DIND_FORWARD_ENV_PREFIXES="EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_"
    export DIND_FORWARD_ENV_VARS="CI_SKYSCAN_STARTUP_JSON"
    # What to run inside the outer container after docker load
    export DIND_OUTER_CMD='python -m ewms_pilot'
    # Optional: pass extra docker args if you need them
    # export DIND_EXTRA_ARGS="..."

    # run (curl script first)
    tmp_for_dnd_sh=$(mktemp -d)
    curl -fsSL "$CI_SCRIPT_URL_DIND_RUN" -o "$tmp_for_dnd_sh/run-dind.sh"
    chmod +x "$tmp_for_dnd_sh/run-dind.sh"
    "$tmp_for_dnd_sh/run-dind.sh"

# ─────────────── Case: Apptainer-in-Docker ───────────────
elif [[ "${_CI_SCANNER_CONTAINER_PLATFORM}" == "apptainer" ]]; then

    # apptainer-specific pilot env vars
    export EWMS_PILOT_TASK_IMAGE="$_SCANNER_IMAGE_APPTAINER"
    export _EWMS_PILOT_APPTAINER_IMAGE_DIRECTORY_MUST_BE_PRESENT=True

    # run
    docker run --rm \
        --privileged \
        --network="$_CI_DOCKER_NETWORK_FOR_APPTAINER_IN_DOCKER" \
        \
        -v "$tmp_rootdir:$tmp_rootdir" \
        -v "$(dirname "$CI_SKYSCAN_STARTUP_JSON"):$(dirname "$CI_SKYSCAN_STARTUP_JSON")":ro \
        -v "$_SCANNER_IMAGE_APPTAINER:$_SCANNER_IMAGE_APPTAINER":ro \
        \
        --env CI_SKYSCAN_STARTUP_JSON="$CI_SKYSCAN_STARTUP_JSON" \
        $(env | grep -E '^(EWMS_|_EWMS_)' | cut -d'=' -f1 | sed 's/^/--env /') \
        \
        "$_PILOT_IMAGE_FOR_APPTAINER_IN_DOCKER"

# ─────────────── Case: Unknown??? ───────────────
else
    echo "::error::cannot launch worker — unknown '_CI_SCANNER_CONTAINER_PLATFORM=$_CI_SCANNER_CONTAINER_PLATFORM'"
    exit 2
fi
