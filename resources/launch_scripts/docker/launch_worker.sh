#!/bin/bash
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
export EWMS_PILOT_TASK_IMAGE="$DOCKER_IMAGE_TAG"
export EWMS_PILOT_TASK_ARGS="python -m skymap_scanner.client.reco_icetray --infile {{INFILE}} --outfile {{OUTFILE}} --client-startup-json $CI_SKYSCAN_STARTUP_JSON"
json_var=$(env | grep '^SKYSCAN_' | awk -F= '{printf "\"%s\":\"%s\",", $1, $2}' | sed 's/,$//') # must remove last comma
json_var="{$json_var}"
export EWMS_PILOT_TASK_ENV_JSON="$json_var"

export _EWMS_PILOT_DOCKER_SHM_SIZE="6gb" # this only needed in ci--the infra would set this in prod

# file types -- controls intermittent serialization
export EWMS_PILOT_INFILE_EXT="JSON"
export EWMS_PILOT_OUTFILE_EXT="JSON"

# to-client queue
export EWMS_PILOT_QUEUE_INCOMING="$SKYSCAN_MQ_TOCLIENT"
export EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN="$SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN"
export EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE="$SKYSCAN_MQ_TOCLIENT_BROKER_TYPE"
export EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS="$SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS"
export EWMS_PILOT_TIMEOUT_QUEUE_INCOMING="$SKYSCAN_MQ_TIMEOUT_TO_CLIENTS"
#
# from-client queue
export EWMS_PILOT_QUEUE_OUTGOING="$SKYSCAN_MQ_FROMCLIENT"
export EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN="$SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN"
export EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE="$SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE"
export EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS="$SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS"

ENV="$(dirname $tmp_rootdir)/pyenv-$(basename $tmp_rootdir)"
pip install virtualenv
virtualenv --python python3 "$ENV"
. "$ENV"/bin/activate
pip install --upgrade pip
pip install ewms-pilot[rabbitmq]
python -m ewms_pilot
