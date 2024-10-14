#!/bin/bash
set -ex # file is sourced so turn off at end

########################################################################
#
# Export many environment variables needed to run a local scan
#
# NOTE: source this file
#
########################################################################

export SKYSCAN_SKYDRIVER_SCAN_ID=$(uuidgen)

# to-client queue
# -> server
export SKYSCAN_MQ_TOCLIENT="to-clients-$SKYSCAN_SKYDRIVER_SCAN_ID"
export SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN=${SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN:-""} # note: set in ci job
export SKYSCAN_MQ_TOCLIENT_BROKER_TYPE=${SKYSCAN_MQ_TOCLIENT_BROKER_TYPE:-"rabbitmq"}
export SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS=${SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS:-""} # note: set in ci job
# -> worker/client/pilot
# note: set in launch_worker.sh
#
# from-client queue
# -> server
export SKYSCAN_MQ_FROMCLIENT="from-clients-$SKYSCAN_SKYDRIVER_SCAN_ID"
export SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN=${SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN:-""} # note: set in ci job
export SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE=${SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE:-"rabbitmq"}
export SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS=${SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS:-""} # note: set in ci job
# -> worker/client/pilot
# note: set in launch_worker.sh

# timeouts -- these are listed in order of occurrence
# -> worker/client/pilot
export EWMS_PILOT_TIMEOUT_QUEUE_WAIT_FOR_FIRST_MESSAGE=${EWMS_PILOT_TIMEOUT_QUEUE_WAIT_FOR_FIRST_MESSAGE:-60}
export EWMS_PILOT_TIMEOUT_QUEUE_INCOMING=${EWMS_PILOT_TIMEOUT_QUEUE_INCOMING:-5}
export EWMS_PILOT_TASK_TIMEOUT=${EWMS_PILOT_TASK_TIMEOUT:-$((1 * 10))} # $((60 * 10))} # TODO - adjust / add option to pilot to not exit on task timeouts (just nack)
export EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR=${EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR:-"True"}
export EWMS_PILOT_OKAY_ERRORS=${EWMS_PILOT_OKAY_ERRORS:-"TimeoutError"} # this is a space-delimited list
#      ^^^ if EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR=false (or similar: no, 0, etc.), then this var is ignored
# -> server
export SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS=${SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS:-$((60 * 10))} # just need a big value -- only used to detect MIA workers (it isn't important in a successful scan)
# other/misc
# -> worker/client/pilot
export SKYSCAN_MINI_TEST=${SKYSCAN_MINI_TEST:-'yes'}
export SKYSCAN_LOG=${SKYSCAN_LOG:-"DEBUG"}
export SKYSCAN_LOG_THIRD_PARTY=${SKYSCAN_LOG_THIRD_PARTY:-"INFO"}
# -> worker/client/pilot
export EWMS_PILOT_KEEP_ALL_TASK_FILES="True" # don't delete stderr/stdout files

set +ex # file is sourced so turn off
