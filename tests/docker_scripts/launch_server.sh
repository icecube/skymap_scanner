#!/bin/sh

# From the README.md

set -x

docker run --network="host" --rm -i $1 skymap_scanner.server \
    --event-pkl $SKYSCAN_EVENT_PKL \
    --cache-dir $SKYSCAN_CACHE_DIR \
    --broker $PULSAR_ADDRESS \
    --auth-token $PULSAR_AUTH \
    --log DEBUG