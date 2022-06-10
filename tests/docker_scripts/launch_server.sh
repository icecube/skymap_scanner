#!/bin/sh

set -x

mkdir "$(pwd)"/$SKYSCAN_CACHE_DIR
docker run --network="host" --rm -i \
    --mount type=bind,source="$(pwd)"/$SKYSCAN_CACHE_DIR,target=/local/$SKYSCAN_CACHE_DIR \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    --env PY_COLORS=1 \
    $1 skymap_scanner.server \
    --event-file $2 \
    --cache-dir /local/$SKYSCAN_CACHE_DIR \
    --gcd-dir /local/gcd-dir \
    --broker $PULSAR_ADDRESS \
    --log DEBUG \
    --mini-test-scan