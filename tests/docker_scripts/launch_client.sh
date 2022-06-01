#!/bin/sh

set -x

mkdir "$(pwd)"/$SKYSCAN_DEBUG_DIR
docker run --network="host" --rm -i \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    --mount type=bind,source="$(pwd)"/$SKYSCAN_DEBUG_DIR,target=/local/$SKYSCAN_DEBUG_DIR \
    --env PY_COLORS=1 \
    $1 skymap_scanner.client \
    --event-name $SKYSCAN_EVENT_PKL \
    --broker $PULSAR_ADDRESS \
    --log DEBUG \
    --debug-directory /local/$SKYSCAN_DEBUG_DIR