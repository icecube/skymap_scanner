#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 producer $2 --broker pulsar://localhost:6650 --nside 1 -n $3