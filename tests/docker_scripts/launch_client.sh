#!/bin/sh

# From the README.md

set -x

docker run --network="host" --rm -i $1 skymap_scanner.client \
    --event-id $SKYSCAN_EVENT \
    --broker localhost \
    --log DEBUG