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

########################################################################
# Validate args

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

########################################################################
# Check required env vars

if [ -z "$SKYSCAN_CACHE_DIR" ] || [ -z "$SKYSCAN_OUTPUT_DIR" ] || [ -z "$SKYSCAN_DEBUG_DIR" ]; then
    echo "required env vars: SKYSCAN_CACHE_DIR, SKYSCAN_OUTPUT_DIR, SKYSCAN_DEBUG_DIR"
    # will fail in mkdirs below...
fi
mkdir $SKYSCAN_CACHE_DIR
mkdir $SKYSCAN_OUTPUT_DIR
mkdir $SKYSCAN_DEBUG_DIR

########################################################################
# Misc setup

if [ -z "$_PREDICTIVE_SCANNING_THRESHOLD" ]; then
    arg_predictive_scanning_threshold=""
else
    arg_predictive_scanning_threshold="--predictive-scanning-threshold $_PREDICTIVE_SCANNING_THRESHOLD"
fi

declare -A pidmap # map of background pids to wait on

export CI_SKYSCAN_STARTUP_JSON="$(pwd)/dir-for-startup-json/startup.json" # export for launch_worker.sh
mkdir "$(dirname "$CI_SKYSCAN_STARTUP_JSON")"

########################################################################
# Launch Server

docker run --network="host" --rm \
    --mount type=bind,source="$(dirname "$_EVENTS_FILE")",target=/local/event,readonly \
    --mount type=bind,source="$SKYSCAN_CACHE_DIR",target=/local/cache \
    --mount type=bind,source="$SKYSCAN_OUTPUT_DIR",target=/local/output \
    --mount type=bind,source="$(dirname "$CI_SKYSCAN_STARTUP_JSON")",target=/local/startup \
    --env PY_COLORS=1 \
    $(env | grep '^SKYSCAN_' | cut -d'=' -f1 | sed 's/^/--env /') \
    $(env | grep '^EWMS_' | cut -d'=' -f1 | sed 's/^/--env /') \
    --env "EWMS_PILOT_TASK_TIMEOUT=${EWMS_PILOT_TASK_TIMEOUT:-900}" \
    icecube/skymap_scanner:"${SKYSCAN_DOCKER_IMAGE_TAG:-"latest"}" \
    python -m skymap_scanner.server \
    --reco-algo $_RECO_ALGO \
    --event-file "/local/event/$(basename "$_EVENTS_FILE")" \
    --cache-dir /local/cache \
    --output-dir /local/output \
    --client-startup-json "/local/startup/$(basename $CI_SKYSCAN_STARTUP_JSON)" \
    --nsides $_NSIDES \
    $arg_predictive_scanning_threshold \
    --real-event \
    2>&1 | tee "$outdir"/server.out \
    &
pidmap["$!"]="central server"

########################################################################
# Wait for startup.json

./wait_for_file.sh $CI_SKYSCAN_STARTUP_JSON $WAIT_FOR_STARTUP_JSON

########################################################################
# Launch Workers that each run a Pilot which each run Skyscan Clients

launch_scripts_dir=$(realpath "./docker/")
echo "Launching $nworkers workers"
export EWMS_PILOT_TASK_TIMEOUT=${EWMS_PILOT_TASK_TIMEOUT:-"1800"} # 30 mins
for i in $(seq 1 $nworkers); do
    dir="$outdir/worker-$i/"
    mkdir -p $dir
    cd $dir
    $launch_scripts_dir/launch_worker.sh >>$dir/pilot.out 2>&1 &
    pidmap["$!"]="worker #$i"
    echo -e "\tworker #$i launched"
done

########################################################################
# Wait for scan components to finish

set +x
echo "Dumping pidmap:"
for pid in "${!pidmap[@]}"; do
    echo "PID: $pid, Identifier: ${pidmap[$pid]}"
done

########################################################################
# Wait for all background processes to complete, looping in reverse order

pids=("${!pidmap[@]}")                                               # get keys
reversed_pids=($(for pid in "${pids[@]}"; do echo $pid; done | tac)) # reverse key order
for pid in "${reversed_pids[@]}"; do
    set -x
    wait $pid
    set +x
    exit_status=$?
    if [[ $exit_status -ne 0 ]]; then
        echo "ERROR: component '${pidmap[$pid]}' failed with status $exit_status"
        sleep 10                         # May need to wait for output files to be written
        kill "${!pidmap[@]}" 2>/dev/null # kill all
        exit 1
    else
        echo "SUCCESS: component '${pidmap[$pid]}' completed successfully"
    fi
done

echo "All components finished successfully"
