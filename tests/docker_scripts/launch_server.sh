#!/bin/sh

# From the README.md

set -x

mkdir $SKYSCAN_CACHE_DIR
docker run --network="host" --rm \
    --mount type=bind,source=$SKYSCAN_CACHE_DIR,target=/local/cache-dir \
    -i $1 skymap_scanner.server \
    --event-pkl $SKYSCAN_EVENT_PKL \
    --cache-dir /local/cache-dir \
    --broker $PULSAR_ADDRESS \
    --auth-token $PULSAR_AUTH \
    --log DEBUG