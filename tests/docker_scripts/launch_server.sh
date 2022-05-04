#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 skymap_scanner.server \
    --event-id $SKYSCAN_EVENT \
    --broker localhost:6650 \
    --log DEBUG
