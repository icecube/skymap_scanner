#!/bin/sh

set -x

mkdir "$(pwd)"/$SKYSCAN_DEBUG_DIR
docker run --network="host" --rm -i \
    --shm-size=6gb \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir,readonly \
    --mount type=bind,source="$(pwd)"/$SKYSCAN_DEBUG_DIR,target=/local/$SKYSCAN_DEBUG_DIR \
    --env PY_COLORS=1 \
    $1 skymap_scanner.client \
    --event-name $2 \
    --broker $PULSAR_ADDRESS \
    --log DEBUG \
    --debug-directory /local/$SKYSCAN_DEBUG_DIR