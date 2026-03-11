#!/bin/bash
set -euo pipefail

########################################################################
#
# Launch a Skymap Scanner worker
#   Uses '_CI_SCANNER_CONTAINER_PLATFORM' to control the mode:
#
# - Docker mode:
#       runs the pilot image (docker) that runs Docker scanner clients
# - Apptainer mode:
#       runs the pilot image (docker) that runs Apptainer scanner clients
#
########################################################################

########################################################################
# Common (platform-agnostic) setup
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

# ─────────────── Case: Docker ───────────────
if [[ "${_CI_SCANNER_CONTAINER_PLATFORM}" == "docker" ]]; then

    # docker-specific pilot env vars
    export EWMS_PILOT_TASK_IMAGE="$_SCANNER_IMAGE_DOCKER"
    export _EWMS_PILOT_DOCKER_SHM_SIZE="6gb"  # CI-specific; prod infra should set this

    # Required env for the helper
    export DOOD_OUTER_IMAGE="$_PILOT_IMAGE_FOR_DOCKER_SCANNER_CLIENT"
    # Network for the outer container
    if [[ -z "${DOOD_NETWORK:-}" ]]; then
        echo "::error::DOOD_NETWORK must be set — this should've been set in '.github/workflows/tests.yml'. Did it not get forwarded to this script?"
        exit 1
    fi
    # Bind dirs: the pilot needs these paths visible at the same locations
    # - tmp_rootdir (RW)
    # - startup.json's parent (RO)
    export DOOD_BIND_RW_DIRS="$tmp_rootdir"
    export DOOD_BIND_RO_DIRS="$(dirname "$CI_SKYSCAN_STARTUP_JSON")"
    # Forward envs by prefix and explicit list
    export DOOD_FORWARD_ENV_PREFIXES="EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_"
    export DOOD_FORWARD_ENV_VARS="CI_SKYSCAN_STARTUP_JSON"

    # run (curl script first)
    tmp_for_dood_sh=$(mktemp -d)
    curl -fsSL "$CI_SCRIPT_URL_DOOD_RUN" -o "$tmp_for_dood_sh/run-dood.sh"
    chmod +x "$tmp_for_dood_sh/run-dood.sh"
    "$tmp_for_dood_sh/run-dood.sh"

# ─────────────── Case: Apptainer ───────────────
elif [[ "${_CI_SCANNER_CONTAINER_PLATFORM}" == "apptainer" ]]; then

    # apptainer-specific pilot env vars
    export EWMS_PILOT_TASK_IMAGE="$_SCANNER_IMAGE_APPTAINER"
    export _EWMS_PILOT_APPTAINER_IMAGE_DIRECTORY_MUST_BE_PRESENT=True

    # run
    docker run --rm \
        --privileged \
        --network=host \
        \
        -v "$tmp_rootdir:$tmp_rootdir" \
        -v "$(dirname "$CI_SKYSCAN_STARTUP_JSON"):$(dirname "$CI_SKYSCAN_STARTUP_JSON")":ro \
        -v "$_SCANNER_IMAGE_APPTAINER:$_SCANNER_IMAGE_APPTAINER":ro \
        \
        --env CI_SKYSCAN_STARTUP_JSON="$CI_SKYSCAN_STARTUP_JSON" \
        $(env | grep -E '^(EWMS_|_EWMS_)' | cut -d'=' -f1 | sed 's/^/--env /') \
        \
        "$_PILOT_IMAGE_FOR_APPTAINER_SCANNER_CLIENT"

# ─────────────── Case: Unknown??? ───────────────
else
    echo "::error::cannot launch worker — unknown '_CI_SCANNER_CONTAINER_PLATFORM=$_CI_SCANNER_CONTAINER_PLATFORM'"
    exit 2
fi
