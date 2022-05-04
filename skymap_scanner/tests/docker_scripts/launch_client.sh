#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 client \
    --event-id $SKYSCAN_EVENT \
    --broker pulsar://localhost:6650 \
    --log DEBUG