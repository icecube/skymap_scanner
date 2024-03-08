#!/bin/bash
set -ex

########################################################################
#
# Runs a scanner instance (server & clients) all on the same machine
#
########################################################################


if [[ $(basename `pwd`) != "launch_scripts" ]]; then
    echo "script must be executed within 'resources/launch_scripts' directory"
    exit 1
fi


if [ -z "$1" ]; then
    echo "Usage: local-scan.sh N_CLIENTS"
    exit 1
fi
if [[ "$1" != +([[:digit:]]) ]]; then
    echo "N_CLIENTS must be a number: $1"
    exit 2
fi
nclients="$1"


if [ -z "$SKYSCAN_CACHE_DIR" ] || [ -z "$SKYSCAN_OUTPUT_DIR" ] || [ -z "$SKYSCAN_DEBUG_DIR" ]; then
    echo "required env vars: SKYSCAN_CACHE_DIR, SKYSCAN_OUTPUT_DIR, SKYSCAN_DEBUG_DIR"
    # will fail in mkdirs below...
fi
mkdir $SKYSCAN_CACHE_DIR
mkdir $SKYSCAN_OUTPUT_DIR
mkdir $SKYSCAN_DEBUG_DIR


if [ -z "$_PREDICTIVE_SCANNING_THRESHOLD" ]; then
    arg_predictive_scanning_threshold=""
else
    arg_predictive_scanning_threshold="--predictive-scanning-threshold $_PREDICTIVE_SCANNING_THRESHOLD"
fi


# Launch Server
./docker/launch_server.sh \
    --reco-algo $_RECO_ALGO \
    --event-file $_EVENTS_FILE \
    --cache-dir $SKYSCAN_CACHE_DIR \
    --output-dir $SKYSCAN_OUTPUT_DIR \
    --client-startup-json ./startup.json \
    --nsides $_NSIDES \
    $arg_predictive_scanning_threshold \
    --real-event \
    2>&1 | tee output \
    &
server_pid=$!


# Wait for startup.json
./wait_for_file.sh ./startup.json $CLIENT_STARTER_WAIT_FOR_STARTUP_JSON


# Launch Clients
echo "Launching $nclients clients"
export EWMS_PILOT_TASK_TIMEOUT=${EWMS_PILOT_TASK_TIMEOUT:-"1800"}  # 30 mins
for i in $( seq 1 $nclients ); do
    ./docker/launch_client.sh \
        --client-startup-json ./startup.json \
        --debug-directory $SKYSCAN_DEBUG_DIR \
        2>&1 | tee output \
        &
    echo -e "\tclient #$i launched"
done


# Wait for scan
# -- we don't actually care about the clients, if they fail or not
# -- if all the clients fail, then the sever times out and we can look at client logs
wait $server_pid