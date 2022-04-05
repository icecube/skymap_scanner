#!/bin/sh

# From the README.md

set -x

docker run --rm -v $PWD:/mnt -i $1 saver --broker pulsar://localhost:6650 --nside 16 -n $2 -o $3