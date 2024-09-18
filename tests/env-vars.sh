#!/bin/bash
set -ex # file is sourced so turn off at end

export SKYSCAN_SKYDRIVER_SCAN_ID=$(uuidgen)

# export SKYSCAN_CACHE_DIR=$PWD/cache-dir -- rely on user value
# export SKYSCAN_OUTPUT_DIR=$PWD/output-dir -- rely on user value

# to-client queue
export SKYSCAN_MQ_TOCLIENT="to-clients-$SKYSCAN_SKYDRIVER_SCAN_ID"
export SKYSCAN_MQ_TOCLIENT_BROKER_TYPE=${SKYSCAN_MQ_TOCLIENT_BROKER_TYPE:-"rabbitmq"}
#
# from-client queue
export SKYSCAN_MQ_FROMCLIENT="from-clients-$SKYSCAN_SKYDRIVER_SCAN_ID"
export SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE=${SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE:-"rabbitmq"}
# note: address & auth env vars are in ci job(s)

export EWMS_PILOT_TASK_TIMEOUT=${EWMS_PILOT_TASK_TIMEOUT:-600}
export EWMS_PILOT_DUMP_SUBPROC_OUTPUT=${EWMS_PILOT_DUMP_SUBPROC_OUTPUT:-"True"}

# export SKYSCAN_DEBUG_DIR=debug-pkl-dir -- rely on user value
export SKYSCAN_MQ_TIMEOUT_TO_CLIENTS=${SKYSCAN_MQ_TIMEOUT_TO_CLIENTS:-5}
export SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS=${SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS:-600}
# export SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE=0

export SKYSCAN_DOCKER_IMAGE_TAG=${SKYSCAN_DOCKER_IMAGE_TAG:-"local"}
export SKYSCAN_MINI_TEST=${SKYSCAN_MINI_TEST:-'yes'}
export SKYSCAN_LOG=${SKYSCAN_LOG:-"DEBUG"}
export SKYSCAN_LOG_THIRD_PARTY=${SKYSCAN_LOG_THIRD_PARTY:-"INFO"}

export WAIT_FOR_STARTUP_JSON=${WAIT_FOR_STARTUP_JSON:-60}

set +ex # file is sourced so turn off
