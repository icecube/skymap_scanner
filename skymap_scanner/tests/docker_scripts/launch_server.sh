#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 server $SKYSCAN_EVENT_URL --broker pulsar://localhost:6650 --nside 1 -n $SKYSCAN_TEST_EVENT