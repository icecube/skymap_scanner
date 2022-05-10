#!/bin/sh

# From the README.md

set -x

mkdir "$(pwd)"/$SKYSCAN_CACHE_DIR
docker run --network="host" --rm -i \
    --mount type=bind,source="$(pwd)"/$SKYSCAN_CACHE_DIR,target=/local/$SKYSCAN_CACHE_DIR \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    $1 skymap_scanner.server \
    --event-pkl $SKYSCAN_EVENT_PKL \
    --cache-dir /local/$SKYSCAN_CACHE_DIR \
    --gcd-dir /local/gcd-dir \
    --broker $PULSAR_ADDRESS \
    --log DEBUG