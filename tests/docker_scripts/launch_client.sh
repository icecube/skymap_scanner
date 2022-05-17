#!/bin/sh

set -x

docker run --network="host" --rm -i \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    --env PY_COLORS=1 \
    $1 skymap_scanner.client \
    --event-name $SKYSCAN_EVENT_PKL \
    --broker $PULSAR_ADDRESS \
    --log DEBUG