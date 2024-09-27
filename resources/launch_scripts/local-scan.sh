#!/bin/bash
set -ex

########################################################################
#
# Runs a scanner instance (server & workers) all on the same machine
#
########################################################################

if [[ $(basename $(pwd)) != "launch_scripts" ]]; then
    echo "script must be executed within 'resources/launch_scripts' directory"
    exit 1
fi

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: local-scan.sh N_WORKERS OUTPUT_DIR"
    exit 1
fi
if [[ $1 != +([[:digit:]]) ]]; then
    echo "N_WORKERS must be a number: $1"
    exit 2
fi
nworkers="$1"
if [ ! -d $(dirname $2) ]; then
    echo "Directory Not Found: $(dirname $1)"
    exit 2
fi
outdir="$(realpath $2)"
mkdir -p "$outdir"

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

declare -A pidmap # map of background pids to wait on

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
    2>&1 | tee "$outdir"/server.out \
    &
pidmap["$!"]="central server"

# Wait for startup.json
export CI_SKYSCAN_STARTUP_JSON="$(realpath "./startup.json")"
./wait_for_file.sh $CI_SKYSCAN_STARTUP_JSON $WAIT_FOR_STARTUP_JSON

# Launch Workers that each run a Pilot which each run Skyscan Clients
launch_scripts_dir=$(realpath "./docker/")
echo "Launching $nworkers workers"
export EWMS_PILOT_TASK_TIMEOUT=${EWMS_PILOT_TASK_TIMEOUT:-"1800"} # 30 mins
for i in $(seq 1 $nworkers); do
    dir="$outdir/worker-$i/"
    mkdir -p $dir
    cd $dir
    $launch_scripts_dir/launch_worker.sh \
        --client-startup-json $CI_SKYSCAN_STARTUP_JSON \
        --debug-directory $SKYSCAN_DEBUG_DIR \
        2>&1 | tee $dir/pilot.out \
        &
    pidmap["$!"]="worker #$i"
    echo -e "\tworker #$i launched"
done

# Wait for scan components to finish
while [ ${#pidmap[@]} -gt 0 ]; do
    # Wait for the first finished process
    if ! finished_pid=$(wait -n); then
        echo "ERROR: component '${pidmap[$finished_pid]}' failed"
        sleep 5                          # May need to wait for output files to be written
        kill "${!pidmap[@]}" 2>/dev/null # kill all
        exit 1
    fi
    # Remove the finished PID from the associative array
    unset pidmap["$finished_pid"]
done
