#!/bin/bash
set -euo pipefail
set -e

########################################################################
#
# Runs a scanner instance (server) and request to EWMS for workers
#
########################################################################

########################################################################
# handle cl args

if [ -z "${1-}" ] || [ -z "${2-}" ] || [ -z "${3-}" ] || [ -z "${4-}" ] || [ -z "${5-}" ] || [ -z "${6-}" ]; then
    echo "Usage: ewms-scan.sh N_WORKERS EWMS_URL SKYSCAN_TAG RECO_ALGO N_SIDES PREDICTIVE_SCANNING_THRESHOLD"
    exit 1
else
    N_WORKERS="$1"
    EWMS_URL="$2"
    SKYSCAN_TAG="$3"
    RECO_ALGO="$4"
    N_SIDES="$5"
    PREDICTIVE_SCANNING_THRESHOLD="$6"
fi

# now, validate...

if [[ $N_WORKERS != +([[:digit:]]) ]]; then
    echo "ERROR: N_WORKERS must be a number: $N_WORKERS"
    exit 2
fi

if ! [[ "$PREDICTIVE_SCANNING_THRESHOLD" == "1" || "$PREDICTIVE_SCANNING_THRESHOLD" =~ ^(0?)\.[0-9]+$ ]]; then
    echo "ERROR: PREDICTIVE_SCANNING_THRESHOLD must be '1' or a decimal."
    exit 2
fi

if [ "$(curl --fail-with-body -s -o /dev/null -w "%{http_code}" "https://hub.docker.com/v2/repositories/icecube/skymap_scanner/tags/$SKYSCAN_TAG/")" -eq 200 ]; then
    echo "Tag found on Docker Hub: $SKYSCAN_TAG"
else
    echo "ERROR: Tag not found on Docker Hub: $SKYSCAN_TAG"
    exit 2
fi

########################################################################
# set up python virtual environment

ENV_NAME="skyscan_ewms_pyvenv"
[ ! -d "$ENV_NAME" ] && virtualenv --python python3 "$ENV_NAME"
source "$ENV_NAME"/bin/activate
pip install --upgrade pip
echo "Virtual environment '$ENV_NAME' is now active."

########################################################################
# set up env vars

export SKYSCAN_SKYDRIVER_SCAN_ID=$(uuidgen)

check_and_export_env() {
    if [ -z "${!1}" ]; then
        echo "ERROR: Environment variable '$1' is not set."
        exit 2
    fi
    export "$1"
}

check_and_export_env S3_URL
check_and_export_env S3_ACCESS_KEY_ID
check_and_export_env S3_SECRET_KEY
check_and_export_env S3_BUCKET

export S3_OBJECT_DEST_FILE="${SKYSCAN_SKYDRIVER_SCAN_ID}-s3-json" # no dots allowed

########################################################################
# trap tools -- what to do if things go wrong

add_cleanup() {
    local new_cmd="$1"
    local trap_signal="$2"
    local existing_trap

    echo "Adding cleanup task for $trap_signal: '$new_cmd'"

    # Get the current trap for the specified signal, if any
    existing_trap=$(trap -p "$trap_signal" | sed -E "s/^trap -- '(.*)' $trap_signal/\1/")

    # If empty -> set the new command, else append
    if [[ -z "$existing_trap" ]]; then
        set -x
        trap "$new_cmd" "$trap_signal"
        set +x
    else
        set -x
        trap "$existing_trap; $new_cmd" "$trap_signal"
        set +x
    fi
}

# add first cleanup actions
add_cleanup 'echo "Handling cleanup for exit..."' EXIT
add_cleanup 'echo "Handling cleanup for error..."' ERR
add_cleanup 'echo "Handling cleanup for ctrl+C..."' INT
add_cleanup 'echo "Handling cleanup for SIGTERM..."' TERM

########################################################################
# S3: Generate the GET pre-signed URL  -- server will post here later, ewms needs it now

echo "################################################################################"
echo "Connecting to S3 to get pre-signed GET URL..." && echo

pip install boto3
S3_OBJECT_URL=$(python3 -c '
import os, boto3

s3_client = boto3.client(
    "s3",
    "us-east-1",
    endpoint_url=os.environ["S3_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
)

# get GET url
get_url = s3_client.generate_presigned_url(
    "get_object",
    Params={
        "Bucket": os.environ["S3_BUCKET"],
        "Key": os.environ["S3_OBJECT_DEST_FILE"],
    },
    ExpiresIn=24 * 60 * 60,  # seconds
)
print(get_url)
')

echo $S3_OBJECT_URL

########################################################################
# request workers on ewms

echo "################################################################################"
echo "Requesting to EWMS..." && echo

export POST_REQ=$(
    cat <<EOF
{
    "public_queue_aliases": ["to-client-queue", "from-client-queue"],
    "tasks": [
        {
            "cluster_locations": ["sub-2"],
            "input_queue_aliases": ["to-client-queue"],
            "output_queue_aliases": ["from-client-queue"],
            "task_image": "/cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:$SKYSCAN_TAG",
            "task_args": "python -m skymap_scanner.client --infile {{INFILE}} --outfile {{OUTFILE}} --client-startup-json {{DATA_HUB}}/startup.json",
            "task_env": {"todo":"remove_this"},
            "init_image": "/cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:$SKYSCAN_TAG",
            "init_args": "bash -c \"curl --fail-with-body --max-time 60 -o {{DATA_HUB}}/startup.json '$S3_OBJECT_URL'\" ",
            "init_env": {"todo":"remove_this"},
            "n_workers": $N_WORKERS,
            "pilot_config": {
                "tag": "${PILOT_TAG:-'latest'}",
                "environment": {
                    "EWMS_PILOT_INIT_TIMEOUT": $((1 * 60)),
                    "EWMS_PILOT_TASK_TIMEOUT": $((1 * 60 * 60)),
                    "EWMS_PILOT_TIMEOUT_QUEUE_WAIT_FOR_FIRST_MESSAGE": $((10 * 60)),
                    "EWMS_PILOT_TIMEOUT_QUEUE_INCOMING": $((5 * 60)),
                    "EWMS_PILOT_CONTAINER_DEBUG": "True",
                    "EWMS_PILOT_INFILE_EXT": ".json",
                    "EWMS_PILOT_OUTFILE_EXT": ".json"
                },
                "input_files": []
            },
            "worker_config": {
                "do_transfer_worker_stdouterr": true,
                "max_worker_runtime": $((2 * 60 * 60)),
                "n_cores": 1,
                "priority": 99,
                "worker_disk": "512M",
                "worker_memory": "8G",
                "condor_requirements": "HAS_CVMFS_icecube_opensciencegrid_org && has_avx && has_avx2"
            }
        }
    ]
}
EOF
)

echo "$POST_REQ"

# Validate JSON
if ! echo "$POST_REQ" | jq empty; then
    echo "Error: Invalid JSON format"
    exit 1
fi

# Make POST request with the multiline JSON data
echo "requesting workflow..."
pip install wipac-rest-tools
POST_RESP=$(python3 -c '
import os, rest_tools, json, pathlib
rc = rest_tools.client.SavedDeviceGrantAuth(
    "https://ewms-dev.icecube.aq",
    token_url="https://keycloak.icecube.wisc.edu/auth/realms/IceCube",
    filename=str(pathlib.Path("~/device-refresh-token").expanduser().resolve()),
    client_id="ewms-dev-public",
    retries=0,
)
res = rc.request_seq("POST", "/v0/workflows", json.loads(os.environ["POST_REQ"]))
print(json.dumps(res))
')
echo "$POST_RESP" | jq . -M --indent 4 # Format JSON with 4 spaces

export WORKFLOW_ID=$(echo "$POST_RESP" | jq -r '.workflow.workflow_id')
echo $WORKFLOW_ID
QUEUE_TOCLIENT=$(echo "$POST_RESP" | jq -r '.task_directives[0].input_queues[0]')
echo $QUEUE_TOCLIENT
QUEUE_FROMCLIENT=$(echo "$POST_RESP" | jq -r '.task_directives[0].output_queues[0]')
echo $QUEUE_FROMCLIENT

########################################################################
# abort the workflow if things go wrong

abort() {
    local workflow_id=$1
    echo "ABORTING WORKFLOW..."
    local resp=$(python3 -c "
import os, rest_tools, json, pathlib
rc = rest_tools.client.SavedDeviceGrantAuth(
    'https://ewms-dev.icecube.aq',
    token_url='https://keycloak.icecube.wisc.edu/auth/realms/IceCube',
    filename=str(pathlib.Path('~/device-refresh-token').expanduser().resolve()),
    client_id='ewms-dev-public',
    retries=0,
)
workflow_id = os.environ['WORKFLOW_ID']
res = rc.request_seq('POST', f'/v0/workflows/{workflow_id}/actions/abort')
print(json.dumps(res))
" WORKFLOW_ID=$workflow_id)
    echo "$resp" | jq . -M --indent 4 # Format JSON with 4 spaces
}

# add_cleanup 'abort $WORKFLOW_ID' EXIT -- not needed
add_cleanup 'abort $WORKFLOW_ID' ERR
add_cleanup 'abort $WORKFLOW_ID' INT
add_cleanup 'abort $WORKFLOW_ID' TERM

########################################################################
# in the background, check if things on ewms have changed

check_ewms_changes() {
    local workflow_id=$1
    local prev_wf_response=""
    local prev_tf_response=""

    while true; do
        sleep 15

        # Step 1: Get workflow associated with the workflow_id
        local wf_resp=$(python3 -c "
import os, rest_tools, json, pathlib
rc = rest_tools.client.SavedDeviceGrantAuth(
    'https://ewms-dev.icecube.aq',
    token_url='https://keycloak.icecube.wisc.edu/auth/realms/IceCube',
    filename=str(pathlib.Path('~/device-refresh-token').expanduser().resolve()),
    client_id='ewms-dev-public',
    retries=0,
)
# Perform POST request to get taskforces by workflow_id
workflow_id = os.environ['WORKFLOW_ID']
res = rc.request_seq('GET', f'/v0/workflows/{workflow_id}')
print(json.dumps(res))
" WORKFLOW_ID=$workflow_id 2>/dev/null)

        # Step 2: Compare the current workflow response with the previous one
        if [[ $wf_resp != "$prev_wf_response" ]]; then
            echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
            echo "~~ The EWMS workflow object has updated:                                          ~~"
            echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
            date
            # If the response has changed, print it and update the previous response
            echo "$wf_resp" | jq . -M --indent 4 # Format JSON with 4 spaces
            prev_wf_response="$wf_resp"
        fi

        # Step 3: Get taskforces associated with the workflow_id
        local tf_resp=$(python3 -c "
import os, rest_tools, json, pathlib
rc = rest_tools.client.SavedDeviceGrantAuth(
    'https://ewms-dev.icecube.aq',
    token_url='https://keycloak.icecube.wisc.edu/auth/realms/IceCube',
    filename=str(pathlib.Path('~/device-refresh-token').expanduser().resolve()),
    client_id='ewms-dev-public',
    retries=0,
)
# Perform POST request to get taskforces by workflow_id
res = rc.request_seq('POST', '/v0/query/taskforces', {'query':{'workflow_id': os.environ['WORKFLOW_ID']}})
print(json.dumps(res))
" WORKFLOW_ID=$workflow_id 2>/dev/null)

        # Step 4: Compare the current taskforces response with the previous one
        if [[ $tf_resp != "$prev_tf_response" ]]; then
            echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
            echo "~~ The EWMS taskforce object(s) have updated:                                 ~~"
            echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
            date
            # If the response has changed, print it and update the previous response
            echo "$tf_resp" | jq . -M --indent 4 # Format JSON with 4 spaces
            prev_tf_response="$tf_resp"
        fi
    done
}

check_ewms_changes "$WORKFLOW_ID" &
check_changes_pid=$!
add_cleanup 'kill $check_changes_pid 2>/dev/null' EXIT
add_cleanup 'kill $check_changes_pid 2>/dev/null' ERR
add_cleanup 'kill $check_changes_pid 2>/dev/null' INT
add_cleanup 'kill $check_changes_pid 2>/dev/null' TERM

########################################################################
# get queue connection info

echo "################################################################################"
echo "Getting MQ info..." && echo

mqprofiles=$(python3 -c '
import os, rest_tools, pathlib, time, json
rc = rest_tools.client.SavedDeviceGrantAuth(
    "https://ewms-dev.icecube.aq",
    token_url="https://keycloak.icecube.wisc.edu/auth/realms/IceCube",
    filename=str(pathlib.Path("~/device-refresh-token").expanduser().resolve()),
    client_id="ewms-dev-public",
    retries=0,
)

workflow_id = os.environ["WORKFLOW_ID"]
mqprofiles: list[dict] = []
# loop until mqprofiles is not empty and all "is_activated" fields are true
while not (mqprofiles and all(m["is_activated"] for m in mqprofiles)):
    time.sleep(10)
    mqprofiles = (
        rc.request_seq(
            "GET",
            f"/v0/mqs/workflows/{workflow_id}/mq-profiles/public",
        )
    )["mqprofiles"]

print(json.dumps(mqprofiles))
')
echo "MQ info:"
echo "$mqprofiles" | jq . -M --indent 4 # Format JSON with 4 spaces

# map mqprofiles from the queue names
mqprofile_toclient=$(echo "$mqprofiles" | jq --arg mqid "$QUEUE_TOCLIENT" '.[] | select(.mqid == $mqid)')
mqprofile_fromclient=$(echo "$mqprofiles" | jq --arg mqid "$QUEUE_FROMCLIENT" '.[] | select(.mqid == $mqid)')

# set env vars for vals from the mqprofiles
export SKYSCAN_MQ_TOCLIENT=$(echo "$mqprofile_toclient" | jq -r '.mqid')
export SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN=$(echo "$mqprofile_toclient" | jq -r '.auth_token')
export SKYSCAN_MQ_TOCLIENT_BROKER_TYPE=$(echo "$mqprofile_toclient" | jq -r '.broker_type')
export SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS=$(echo "$mqprofile_toclient" | jq -r '.broker_address')
#
export SKYSCAN_MQ_FROMCLIENT=$(echo "$mqprofile_fromclient" | jq -r '.mqid')
export SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN=$(echo "$mqprofile_fromclient" | jq -r '.auth_token')
export SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE=$(echo "$mqprofile_fromclient" | jq -r '.broker_type')
export SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS=$(echo "$mqprofile_fromclient" | jq -r '.broker_address')

########################################################################
# start server

echo "################################################################################"
echo "Starting local scanner server..." && echo

SCANNER_SERVER_DIR="./scan-dir-$WORKFLOW_ID/"
mkdir $SCANNER_SERVER_DIR

# look at env vars before running
env | grep -E '^(SKYSCAN_|_SKYSCAN_)' | sort || true
env | grep -E '^(EWMS_|_EWMS_)' | sort || true

set -x # let's see this command
sudo -E docker run --network="host" --rm -i \
    $DOCKERMOUNT_ARGS \
    --mount type=bind,source=$(realpath $SCANNER_SERVER_DIR),target=/local/$(basename $SCANNER_SERVER_DIR) \
    $(env | grep -E '^(SKYSCAN_|_SKYSCAN_)' | sort | cut -d'=' -f1 | sed 's/^/--env /') \
    $(env | grep -E '^(EWMS_|_EWMS_)' | sort | cut -d'=' -f1 | sed 's/^/--env /') \
    icecube/skymap_scanner:${SKYSCAN_SERVER_TAG:-$SKYSCAN_TAG} \
    python -m skymap_scanner.server \
    --client-startup-json /local/$(basename $SCANNER_SERVER_DIR)/startup.json \
    --cache-dir /local/$(basename $SCANNER_SERVER_DIR)/cache-dir/ \
    --output-dir /local/$(basename $SCANNER_SERVER_DIR)/results/ \
    --reco-algo "$RECO_ALGO" \
    --predictive-scanning-threshold "$PREDICTIVE_SCANNING_THRESHOLD" \
    --event-file /local/tests/data/realtime_events/run00136766-evt000007637140-GOLD.pkl --real-event \
    --nsides $N_SIDES |
    tee "$SCANNER_SERVER_DIR/server.out" 2>&1 \
    &
server_pid=$!
set +x

sleep 3 # for stdout ordering

export S3_FILE_TO_UPLOAD="$SCANNER_SERVER_DIR/startup.json"

########################################################################
# get startup.json -> put in S3

echo "################################################################################"
echo "Waiting for file $S3_FILE_TO_UPLOAD..." && echo

# wait until the file exists (with a timeout)
found="false"
endtime=$(date -ud "120 seconds" +%s) # wait this long
while [[ $(date -u +%s) -le $endtime ]]; do
    if [[ -e $S3_FILE_TO_UPLOAD ]]; then
        echo "Success, file found!"
        found="true"
        break
    fi
    echo "waiting for file..."
    echo "ls: $SCANNER_SERVER_DIR"
    ls "$SCANNER_SERVER_DIR"
    sleep 5
done
if [[ $found != "true" ]]; then
    echo "ERROR: file not found: $S3_FILE_TO_UPLOAD"
    exit 1
fi

echo && echo "Uploading file ($S3_FILE_TO_UPLOAD) to S3..."

out=$(python3 -c '
import os, boto3, requests, pathlib

s3_client = boto3.client(
    "s3",
    "us-east-1",
    endpoint_url=os.environ["S3_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
)

# POST
upload_details = s3_client.generate_presigned_post(
    os.environ["S3_BUCKET"],
    os.environ["S3_OBJECT_DEST_FILE"]
)
filepath = pathlib.Path(os.environ["S3_FILE_TO_UPLOAD"])
with open(filepath, "rb") as f:
    response = requests.post(
        upload_details["url"],
        data=upload_details["fields"],
        files={"file": (filepath.name, f)},  # maps filename to obj
    )
print(f"Upload response: {response.status_code}")
print(str(response.content))
')
echo $out

########################################################################
# wait for scan to finish

echo "################################################################################"
echo "Waiting for scan to finish..." && echo

# dump all content, then dump new content in realtime
tail -n +1 -f "$SCANNER_SERVER_DIR/server.out" &

wait $server_pid
echo "The scan finished!"

########################################################################
# deactivate ewms workflow

echo "################################################################################"
echo "Deactivating the workflow..." && echo

POST_RESP=$(python3 -c "
import os, rest_tools, json, pathlib
rc = rest_tools.client.SavedDeviceGrantAuth(
    'https://ewms-dev.icecube.aq',
    token_url='https://keycloak.icecube.wisc.edu/auth/realms/IceCube',
    filename=str(pathlib.Path('~/device-refresh-token').expanduser().resolve()),
    client_id='ewms-dev-public',
    retries=0,
)
workflow_id = os.environ['WORKFLOW_ID']
res = rc.request_seq('POST', f'/v0/workflows/{workflow_id}/actions/finished')
print(json.dumps(res))
" WORKFLOW_ID=$workflow_id)
echo "$POST_RESP" | jq . -M --indent 4 # Format JSON with 4 spaces
sleep 120  # TODO - use smarter logic

########################################################################
# look at result

echo "################################################################################"
echo "The scan was a success!" && echo

echo "The results:"
ls "$SCANNER_SERVER_DIR/results/"

echo "Script finished."
