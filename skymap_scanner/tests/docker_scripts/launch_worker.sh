#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 worker --broker pulsar://localhost:6650