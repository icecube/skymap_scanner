#!/bin/sh

# From the README.md

set -x

docker run --network="host" --rm -i $1 skymap_scanner.alert_listener \
    --cache-dir $SKYSCAN_CACHE_DIR \
    --event-id $SKYSCAN_EVENT \
    --broker $PULSAR_ADDRESS \
    --log DEBUG
