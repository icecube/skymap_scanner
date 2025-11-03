#!/bin/bash
set -euo pipefail
set -ex

########################################################################
#
# Launch a Skymap Scanner worker
#
# Run worker on ewms pilot
#
########################################################################

# establish pilot's root path
tmp_rootdir="$(pwd)/pilot-$(uuidgen)"
mkdir $tmp_rootdir
cd $tmp_rootdir
export EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST="$tmp_rootdir"

# mark startup.json's dir to be bind-mounted into the task container (by the pilot)
# -> check that the dir only has one file, otherwise we may end up binding extra dirs
python -c 'import os; assert os.listdir(os.path.dirname(os.environ["CI_SKYSCAN_STARTUP_JSON"])) == ["startup.json"]'
export EWMS_PILOT_EXTERNAL_DIRECTORIES="$(dirname "$CI_SKYSCAN_STARTUP_JSON")"

# task image, args, env
if [ -n "${_SCANNER_IMAGE_APPTAINER:-}" ]; then
    if [[ "$_SCANNER_IMAGE_APPTAINER" == *.sif ]]; then
        # place a duplicate of the file b/c the pilot transforms this into sandbox/dir format, so there are race conditions w/ parallelizing
        export EWMS_PILOT_TASK_IMAGE="$tmp_rootdir/$(basename "$_SCANNER_IMAGE_APPTAINER")"
        cp "$_SCANNER_IMAGE_APPTAINER" "$EWMS_PILOT_TASK_IMAGE"
        export _EWMS_PILOT_APPTAINER_IMAGE_DIRECTORY_MUST_BE_PRESENT=False
    else
        # already in sandbox/dir format
        export EWMS_PILOT_TASK_IMAGE="$_SCANNER_IMAGE_APPTAINER"
        export _EWMS_PILOT_APPTAINER_IMAGE_DIRECTORY_MUST_BE_PRESENT=True
    fi
    export _EWMS_PILOT_SCANNER_CONTAINER_PLATFORM="apptainer"
else
    export EWMS_PILOT_TASK_IMAGE="$_SCANNER_IMAGE_DOCKER"
    export _EWMS_PILOT_SCANNER_CONTAINER_PLATFORM="docker" # NOTE: technically not needed b/c this is the default value
    export _EWMS_PILOT_DOCKER_SHM_SIZE="6gb"       # this only needed in ci--the infra would set this in prod
fi
export EWMS_PILOT_TASK_ARGS="python -m skymap_scanner.client --infile {{INFILE}} --outfile {{OUTFILE}} --client-startup-json $CI_SKYSCAN_STARTUP_JSON"
json_var=$(env | grep -E '^(SKYSCAN_|_SKYSCAN_)' | awk -F= '{printf "\"%s\":\"%s\",", $1, $2}' | sed 's/,$//') # must remove last comma
json_var="{$json_var}"
export EWMS_PILOT_TASK_ENV_JSON="$json_var"

# file types -- controls intermittent serialization
export EWMS_PILOT_INFILE_EXT="JSON"
export EWMS_PILOT_OUTFILE_EXT="JSON"

# Load JSON values
export EWMS_PILOT_QUEUE_INCOMING=$(jq -r '.toclient.name' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN=$(jq -r '.toclient.auth_token' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE=$(jq -r '.toclient.broker_type' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS=$(jq -r '.toclient.broker_address' "$_EWMS_JSON_ON_HOST")

export EWMS_PILOT_QUEUE_OUTGOING=$(jq -r '.fromclient.name' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN=$(jq -r '.fromclient.auth_token' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE=$(jq -r '.fromclient.broker_type' "$_EWMS_JSON_ON_HOST")
export EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS=$(jq -r '.fromclient.broker_address' "$_EWMS_JSON_ON_HOST")


# run!
docker run --rm \
    $( \
        [[ $_SCANNER_CONTAINER_PLATFORM == "docker" ]] \
        && echo "--network=$_CI_DOCKER_NETWORK_FOR_DOCKER_IN_DOCKER --privileged --hostname=syscont" \
        || echo "--network=$_CI_DOCKER_NETWORK_FOR_APPTAINER_IN_DOCKER" \
    ) \
    \
    -v "${tmp_rootdir}:${tmp_rootdir}" \
    -v "$(dirname "${CI_SKYSCAN_STARTUP_JSON}"):$(dirname "${CI_SKYSCAN_STARTUP_JSON}")":ro \
    $( [[ $_SCANNER_CONTAINER_PLATFORM == "apptainer" ]] \
        && echo "-v $_SCANNER_IMAGE_APPTAINER:$_SCANNER_IMAGE_APPTAINER):ro" \
        || echo "" \
    ) \
    \
    --env CI_SKYSCAN_STARTUP_JSON="${CI_SKYSCAN_STARTUP_JSON}" \
    \
    $(env | grep -E '^(EWMS_|_EWMS_)' | cut -d'=' -f1 | sed 's/^/--env /') \
    \
    $( [[ $_SCANNER_CONTAINER_PLATFORM == "docker" ]] \
        && echo "$_PILOT_IMAGE_FOR_DOCKER_IN_DOCKER" \
        || echo "$_PILOT_IMAGE_FOR_APPTAINER_IN_DOCKER" \
    )
