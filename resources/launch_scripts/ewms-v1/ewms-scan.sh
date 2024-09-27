#!/bin/bash
set -e

########################################################################
#
# Runs a scanner instance (server) and request to EWMS for workers
#
########################################################################

########################################################################
# handle cl args

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: ewms-scan.sh N_WORKERS EWMS_URL SKYSCAN_TAG"
    exit 1
else
    N_WORKERS="$1"
    EWMS_URL="$2"
    SKYSCAN_TAG="$3"
fi

# now, validate...

if [[ $N_WORKERS != +([[:digit:]]) ]]; then
    echo "N_WORKERS must be a number: $N_WORKERS"
    exit 2
fi

if [ "$(curl --fail-with-body -s -o /dev/null -w "%{http_code}" "https://hub.docker.com/v2/repositories/icecube/skymap_scanner/tags/$SKYSCAN_TAG/")" -eq 200 ]; then
    echo "Tag found on Docker Hub: $SKYSCAN_TAG"
else
    echo "ERROR: Tag not found on Docker Hub: $SKYSCAN_TAG"
    exit 2
fi

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
# S3: Generate the GET pre-signed URL  -- server will post here later, ewms needs it now

echo && echo "Connecting to S3 to get pre-signed GET URL..."

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

echo && echo "Requesting to EWMS..."

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
            "task_args": "python -m skymap_scanner.client.reco_icetray --infile {{INFILE}} --outfile {{OUTFILE}} --client-startup-json \$EWMS_TASK_DATA_HUB_DIR/startup.json",
            "init_image": "alpine:latest",
            "init_args": "while ! curl --fail-with-body -o \"\$EWMS_TASK_DATA_HUB_DIR/startup.json\" \"$S3_OBJECT_URL\"; do echo 'Retrying...'; sleep 15; done",
            "n_workers": $N_WORKERS,
            "pilot_config": {
                "image": "latest",
                "environment": {
                    "EWMS_PILOT_TASK_TIMEOUT": "3600"
                },
                "input_files": []
            },
            "worker_config": {
                "do_transfer_worker_stdouterr": true,
                "max_worker_runtime": 600,
                "n_cores": 1,
                "priority": 99,
                "worker_disk": "512M",
                "worker_memory": "512M"
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

echo "$POST_RESP"

export WORKFLOW_ID=$(echo "$POST_RESP" | jq -r '.workflow.workflow_id')
echo $WORKFLOW_ID
QUEUE_TOCLIENT=$(echo "$POST_RESP" | jq -r '.task_directives[0].input_queues[0]')
echo $QUEUE_TOCLIENT
QUEUE_FROMCLIENT=$(echo "$POST_RESP" | jq -r '.task_directives[0].output_queues[0]')
echo $QUEUE_FROMCLIENT

########################################################################
# get queue connection info

echo && echo "Getting MQ info..."
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

echo "$mqprofiles"

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

echo && echo "Starting local scanner server..."

SCANNER_SERVER_DIR="./scan-dir-$WORKFLOW_ID/"
mkdir $SCANNER_SERVER_DIR

set -x # let's see this command
sudo docker run --network="host" --rm -i \
    $DOCKERMOUNT_ARGS \
    --mount type=bind,source=$(realpath $SCANNER_SERVER_DIR),target=/local/$(basename $SCANNER_SERVER_DIR) \
    $(env | grep '^SKYSCAN_' | cut -d'=' -f1 | sed 's/^/--env /') \
    $(env | grep '^EWMS_' | cut -d'=' -f1 | sed 's/^/--env /') \
    icecube/skymap_scanner:${SKYSCAN_SERVER_TAG:-$SKYSCAN_TAG} \
    python -m skymap_scanner.server \
    --client-startup-json /local/$(basename $SCANNER_SERVER_DIR)/startup.json \
    --cache-dir /local/$(basename $SCANNER_SERVER_DIR)/cache-dir/ \
    --output-dir /local/$(basename $SCANNER_SERVER_DIR)/results/ \
    --reco-algo dummy \
    --event-file /local/tests/data/realtime_events/run00136766-evt000007637140-GOLD.pkl --real-event \
    --nsides 1:0 \
    >"$SCANNER_SERVER_DIR/server.out" 2>&1 \
    &
server_pid=$!
set +x

sleep 3 # for stdout ordering

export S3_FILE_TO_UPLOAD="$SCANNER_SERVER_DIR/startup.json"

########################################################################
# get startup.json -> put in S3

echo && echo "Waiting for file $S3_FILE_TO_UPLOAD..."

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

echo && echo "Waiting for scan to finish..."

# dump all content, then dump new content in realtime
tail -n +1 -f "$SCANNER_SERVER_DIR/server.out" &

wait $server_pid

########################################################################
# look at result

echo && echo "The results:"
ls "$SCANNER_SERVER_DIR/results/"
