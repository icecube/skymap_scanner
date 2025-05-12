#!/bin/bash
set -euo pipefail
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

if [ -z "$CI_SKYSCAN_CACHE_DIR" ] || [ -z "$CI_SKYSCAN_OUTPUT_DIR" ] || [ -z "$CI_SKYSCAN_DEBUG_DIR" ]; then
    echo "required env vars: CI_SKYSCAN_CACHE_DIR, CI_SKYSCAN_OUTPUT_DIR, CI_SKYSCAN_DEBUG_DIR"
    exit 2
fi
mkdir $CI_SKYSCAN_CACHE_DIR
mkdir $CI_SKYSCAN_OUTPUT_DIR
mkdir $CI_SKYSCAN_DEBUG_DIR

########################################################################
# Misc setup

if [ -n "${_PREDICTIVE_SCANNING_THRESHOLD:-}" ]; then
    arg_predictive_scanning_threshold="--predictive-scanning-threshold $_PREDICTIVE_SCANNING_THRESHOLD"
else
    arg_predictive_scanning_threshold=""
fi

declare -A pidmap # map of background pids to wait on

export CI_SKYSCAN_STARTUP_JSON="$(pwd)/dir-for-startup-json/startup.json" # export for launch_worker.sh
mkdir "$(dirname "$CI_SKYSCAN_STARTUP_JSON")"

########################################################################
# Launch Server

if [ -n "${_RUN_THIS_SIF_IMAGE:-}" ]; then
    # SINGULARITY
    export SKYSCAN_EWMS_JSON="$_EWMS_JSON_ON_HOST"
    singularity run "$_RUN_THIS_SIF_IMAGE" \
        python -m skymap_scanner.server \
        --reco-algo $_RECO_ALGO \
        --event-file $_EVENTS_FILE \
        --cache-dir $CI_SKYSCAN_CACHE_DIR \
        --output-dir $CI_SKYSCAN_OUTPUT_DIR \
        --client-startup-json $CI_SKYSCAN_STARTUP_JSON \
        --nsides $_NSIDES \
        --simulated-event \
        2>&1 | tee "$outdir"/server.out \
        &
else
    # DOCKER
    docker run --network="host" --rm \
        --mount type=bind,source="$(dirname "$_EVENTS_FILE")",target=/local/event,readonly \
        --mount type=bind,source="$CI_SKYSCAN_CACHE_DIR",target=/local/cache \
        --mount type=bind,source="$CI_SKYSCAN_OUTPUT_DIR",target=/local/output \
        --mount type=bind,source="$(dirname "$CI_SKYSCAN_STARTUP_JSON")",target=/local/startup \
        --mount type=bind,source="$(dirname "$_EWMS_JSON_ON_HOST")",target=/local/ewms \
        --env PY_COLORS=1 \
        $(env | grep -E '^(SKYSCAN_|_SKYSCAN_)' | cut -d'=' -f1 | sed 's/^/--env /') \
        $(env | grep -E '^(EWMS_|_EWMS_)' | cut -d'=' -f1 | sed 's/^/--env /') \
        --env SKYSCAN_EWMS_JSON="/local/ewms/$(basename "$_EWMS_JSON_ON_HOST")" \
        "$CI_DOCKER_IMAGE_TAG" \
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
fi
pidmap["$!"]="central server"

########################################################################
# Wait for startup.json

./wait_for_file.sh $CI_SKYSCAN_STARTUP_JSON 60

########################################################################
# Launch Workers that each run a Pilot which each run Skyscan Clients

launch_scripts_dir=$(pwd)
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
echo "pidmap:"
for pid in "${!pidmap[@]}"; do
    echo "PID: $pid, Identifier: ${pidmap[$pid]}"
done

########################################################################
# Wait for all background processes to complete, looping in reverse order

# helper function to find the finished process
find_finished_pid() {
    local running_pids=("$@")
    local is_running
    for pid in "${pids[@]}"; do
        is_running=false
        local running_pid
        for running_pid in "${running_pids[@]}"; do
            if [[ $pid == "$running_pid" ]]; then
                is_running=true
                break
            fi
        done
        if ! $is_running; then
            echo "$pid"
            return
        fi
    done
}

# Loop over the number of background tasks -- each time, we'll wait on the FIRST to finish
echo "Waiting on components..."
pids=("${!pidmap[@]}") # get keys
for ((i = 0; i < ${#pids[@]}; i++)); do
    echo "Background jobs before wait:"
    jobs -p
    echo "sleeping for 10s..."
    sleep 10
    set -x
    wait -n # wait for the FIRST to finish
    exit_status=$?
    set +x
    echo "sleeping for 5s..."
    sleep 5 # for our logs

    # find the finished process PID by checking jobs
    running_pids=($(jobs -pr))
    finished_pid=$(find_finished_pid "${running_pids[@]}")
    echo "Process $finished_pid (${pidmap[$finished_pid]}) finished with $exit_status."

    # check if that proc failed
    if [ $exit_status -ne 0 ]; then
        echo "ERROR: A process exited with status $exit_status. Exiting and killing remaining processes."
        # Kill all remaining background processes
        for pid in "${pids[@]}"; do
            sleep 1
            kill "$pid" 2>/dev/null
        done
        sleep 10 # for proc logs
        exit 1
    fi
done

echo "All components finished successfully"
