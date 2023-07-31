#!/bin/bash

########################################################################
#
# Runs a scanner instance (server & clients) at a scale useful for CI
# testing
#
########################################################################

set -x


if [[ $(basename `pwd`) != "launch_scripts" ]]; then
    echo "script must be executed within 'resources/launch_scripts' directory"
    exit 1
fi


mkdir $SKYSCAN_CACHE_DIR
mkdir $SKYSCAN_OUTPUT_DIR


if [ -z "$_PREDICTIVE_SCANNING_THRESHOLD" ]; then
    arg_predictive_scanning_threshold=""
else
    arg_predictive_scanning_threshold="--predictive-scanning-threshold $_PREDICTIVE_SCANNING_THRESHOLD"
fi


# Launch Server
./launch_server.sh \
    --reco-algo $_RECO_ALGO \
    --event-file $_EVENTS_FILE \
    --cache-dir $SKYSCAN_CACHE_DIR \
    --output-dir $SKYSCAN_OUTPUT_DIR \
    --client-startup-json ./startup.json \
    --nsides $_NSIDES \
    $arg_predictive_scanning_threshold \
    --real-event \
    &


# Wait for startup.json
./wait_for_file.sh ./startup.json $CLIENT_STARTER_WAIT_FOR_STARTUP_JSON


# Launch Clients
nclients=$(( $CLIENTS_PER_CPU * $(nproc) ))
echo "Launching $nclients clients"
mkdir $SKYSCAN_DEBUG_DIR
export EWMS_PILOT_TASK_TIMEOUT=1800  # 30 mins
for i in $( seq 1 $nclients ); do
    ./launch_client.sh \
        --client-startup-json ./startup.json \
        --debug-directory $SKYSCAN_DEBUG_DIR \
        &
    echo -e "\tclient #$i launched"
done


# Wait for Everyone
wait -n  # for server
for i in $( seq 1 $nclients ); do
    wait -n  # for client
done