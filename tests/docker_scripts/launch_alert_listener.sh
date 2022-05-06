#!/bin/sh

# From the README.md

set -x

docker run --network="host" --rm -i $1 skymap_scanner.alert_listener \
    --event-pkl $SKYSCAN_EVENT_PKL \
    --server-broker $PULSAR_ADDRESS \
    --server-broker-auth $PULSAR_AUTH \
    --server-log-level DEBUG
