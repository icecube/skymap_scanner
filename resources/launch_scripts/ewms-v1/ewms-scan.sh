#!/bin/bash
set -ex

########################################################################
#
# Runs a scanner instance (server) and request to EWMS for clients
#
########################################################################

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: ewms-scan.sh N_CLIENTS EWMS_URL SKYSCAN_TAG"
    exit 1
else
    N_CLIENTS="$1"
    EWMS_URL="$2"
    SKYSCAN_TAG="$3"
fi

# now, validate...

if [[ "$N_CLIENTS" != +([[:digit:]]) ]]; then
    echo "N_CLIENTS must be a number: $N_CLIENTS"
    exit 2
fi

if [ "$( curl -s -o /dev/null -w "%{http_code}" "https://hub.docker.com/v2/repositories/icecube/skymap_scanner/tags/$SKYSCAN_TAG/" )" -eq 200 ]; then
    echo "Tag found on Docker Hub: $SKYSCAN_TAG"
else
    echo "ERROR: Tag not found on Docker Hub: $SKYSCAN_TAG"
    exit 2
fi


########################################################################
# set up env vars

export SKYSCAN_SKYDRIVER_SCAN_ID=$( uuidgen )


########################################################################
# S3: Generate the GET pre-signed URL  -- server will post here later, ewms needs it now

echo "Connecting to S3 to get pre-signed GET URL..."

S3_OBJECT_DEST_FILE="${SKYSCAN_SKYDRIVER_SCAN_ID}-s3-json"  # no dots allowed

S3_OBJECT_URL=$(python3 -c '
import os, boto3

s3_client = boto3.client(
    "s3",
    "us-east-1",
    endpoint_url=os.environ["S3_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["TMS_S3_SECRET_KEY"],
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

echo "Requesting to EWMS..."

# TODO - ADD INIT TO GET S3 STARTUP JSON

POST_REQ=$(cat <<EOF
{
    "public_queue_aliases": ["to-client-queue", "from-client-queue"],
    "tasks": [
        {
            "cluster_locations": ["sub-2"],
            "input_queue_aliases": ["to-client-queue"],
            "output_queue_aliases": ["from-client-queue"],
            "task_image": "/cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:$SKYSCAN_TAG",
            "task_args": "python -m skymap_scanner.client.reco_icetray --in-pkl {{INFILE}} --out-pkl {{OUTFILE}} --client-startup-json \$INCONTAINER_ENVNAME_TASK_DATA_HUB_DIR/startup.json",
            "n_workers": $N_CLIENTS,
            "pilot_config": {
                "image": "latest",
                "environment": {
                    "EWMS_PILOT_TASK_IMAGE": "alpine:latest",
                    "EWMS_PILOT_TASK_ARGS": "while ! curl -f -o \$INCONTAINER_ENVNAME_TASK_DATA_HUB_DIR/startup.json $S3_OBJECT_URL; do echo 'Retrying...'; sleep 15; done",
                    "EWMS_PILOT_TASK_TIMEOUT": "3600",
                },
                "input_files": [],
            },
            "worker_config": {
                "do_transfer_worker_stdouterr": True,
                "max_worker_runtime": 600,
                "n_cores": 1,
                "priority": 99,
                "worker_disk": "512M",
                "worker_memory": "512M",
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
POST_RESP=$( curl -X POST -H "Content-Type: application/json" -d "$POST_REQ" "${EWMS_URL}/v0/workflows" )
echo "$POST_RESP"

WORKFLOW_ID=$( echo "$POST_RESP" | jq -r '.workflow.workflow_id' )
QUEUE_TOCLIENT=$( echo "$POST_RESP" | jq -r '.task_directives[0].input_queues[0]' )
QUEUE_FROMCLIENT=$( echo "$POST_RESP" | jq -r '.task_directives[0].output_queues[0]' )


########################################################################
# get queue connection info

echo "Getting MQ info..."

# Loop until mqprofiles is not empty and all "is_activated" fields are true
mqprofiles="[]"
while :; do
    response=$( curl -s -X GET "${EWMS_URL}/v0/mqs/workflows/${WORKFLOW_ID}/mq-profiles/public" )
    echo $response

    mqprofiles=$(echo "$response" | jq '.mqprofiles')

    # Check if mqprofiles is not empty and all "is_activated" are true
    activated=$( echo "$mqprofiles" | jq 'length > 0 and all(.[]; .is_activated == true)' )

    if [[ "$activated" == "true" ]]; then
        echo "All queues are activated."
        break
    else
        echo "Queues are not ready, waiting..."
    fi

    sleep 10
done

# map mqprofiles from the queue names
mqprofile_toclient=$( echo "$mqprofiles" | jq --arg mqid "$QUEUE_TOCLIENT" '.[] | select(.mqid == $mqid)' )
mqprofile_fromclient=$( echo "$mqprofiles" | jq --arg mqid "$QUEUE_FROMCLIENT" '.[] | select(.mqid == $mqid)' )

# set env vars for vals from the mqprofiles
export SKYSCAN_MQ_TOCLIENT=$( echo "$mqprofile_toclient" | jq -r '.mqid' )
export SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN=$( echo "$mqprofile_toclient" | jq -r '.auth_token' )
export SKYSCAN_MQ_TOCLIENT_BROKER_TYPE=$( echo "$mqprofile_toclient" | jq -r '.broker_type' )
export SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS=$( echo "$mqprofile_toclient" | jq -r '.broker_address' )
#
export SKYSCAN_MQ_FROMCLIENT=$( echo "$mqprofile_fromclient" | jq -r '.mqid' )
export SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN=$( echo "$mqprofile_fromclient" | jq -r '.auth_token' )
export SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE=$( echo "$mqprofile_fromclient" | jq -r '.broker_type' )
export SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS=$( echo "$mqprofile_fromclient" | jq -r '.broker_address' )


########################################################################
# start server
set -x

echo "Starting local scanner server..."

SCANNER_SERVER_DIR="./scan-dir-$SKYSCAN_SKYDRIVER_SCAN_ID/"
mkdir $SCANNER_SERVER_DIR

docker run --network="host" --rm -i \
    $DOCKERMOUNT_ARGS \
    --mount type=bind,source=$( realpath $SCANNER_SERVER_DIR ),target=/local/$( basename $SCANNER_SERVER_DIR ) \
    $( env | grep '^SKYSCAN_' | awk '$0="--env "$0' ) \
    $( env | grep '^EWMS_' | awk '$0="--env "$0' ) \
    icecube/skymap_scanner:$SKYSCAN_TAG \
    python -m skymap_scanner.server \
    --client-startup-json /local/$( basename $SCANNER_SERVER_DIR )/startup.json \
    --cache-dir /local/$( basename $SCANNER_SERVER_DIR )/cache-dir/ \
    --output-dir /local/$( basename $SCANNER_SERVER_DIR )/results/ \
    --reco-algo dummy \
    --event-file /local/$( basename $SCANNER_SERVER_DIR )/event-file --real-event \
    --nsides 1:0 \
    > "$SCANNER_SERVER_DIR/server.out" 2>&1 \
    &
server_pid=$!

export S3_FILE_TO_UPLOAD="$SCANNER_SERVER_DIR/startup.json"


########################################################################
# get startup.json -> put in S3

echo "Uploading file ($S3_FILE_TO_UPLOAD) to S3..."

out=$(python3 -c '
import os, boto3

s3_client = boto3.client(
    "s3",
    "us-east-1",
    endpoint_url=os.environ["S3_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["TMS_S3_SECRET_KEY"],
)

# POST
upload_details = s3_client.generate_presigned_post(
    os.environ["S3_BUCKET"],
    os.environ["S3_OBJECT_DEST_FILE"]
)
with open(os.environ["S3_FILE_TO_UPLOAD"], "rb") as f:
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

echo "Waiting for scan to finish..."

# dump all content, then dump new content in realtime
tail -n +1 -f "$SCANNER_SERVER_DIR/server.out" &

wait $server_pid


########################################################################
# look at result

ls "$SCANNER_SERVER_DIR/results/"
