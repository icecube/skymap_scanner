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
# request workers on ewms

POST_REQ=$(cat <<EOF
{
    "public_queue_aliases": ["to-client-queue", "from-client-queue"],
    "tasks": [
        {
            "cluster_locations": ["sub-2"],
            "input_queue_aliases": ["to-client-queue"],
            "output_queue_aliases": ["from-client-queue"],
            "task_image": "/cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:$SKYSCAN_TAG",
            "task_args": "cp {{INFILE}} {{OUTFILE}}",  # TODO
            "n_workers": $N_CLIENTS,
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

docker run --network="host" --rm -i \
    $DOCKERMOUNT_ARGS \
    $(env | grep '^SKYSCAN_' | awk '$0="--env "$0') \
    $(env | grep '^EWMS_' | awk '$0="--env "$0') \
    icecube/skymap_scanner:$SKYSCAN_TAG \
    python -m skymap_scanner.server \
    $PY_ARGS

########################################################################
# look at result