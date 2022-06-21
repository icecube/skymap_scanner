#!/bin/sh

set -x

mkdir "$(pwd)"/$SKYSCAN_CACHE_DIR
docker run --network="host" --rm -i \
    --mount type=bind,source="$(pwd)"/$SKYSCAN_CACHE_DIR,target=/local/$SKYSCAN_CACHE_DIR \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir,readonly \
    --mount type=bind,source="$(dirname $2)",target=/local/event,readonly \
    --env PY_COLORS=1 \
    $1 skymap_scanner.server \
    --event-file /local/event/"$(basename $2)" \
    --cache-dir /local/$SKYSCAN_CACHE_DIR \
    --gcd-dir /local/gcd-dir \
    --broker $PULSAR_ADDRESS \
    --log DEBUG \
    --mini-test-variations
    # --min-nside 1 \
    # --max-nside 1