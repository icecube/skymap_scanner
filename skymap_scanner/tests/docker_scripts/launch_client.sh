#!/bin/sh

# From the README.md

set -x

docker run --rm -i $1 client --broker pulsar://localhost:6650