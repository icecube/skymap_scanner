#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 collector --broker pulsar://localhost:6650