#!/bin/bash

set -x

# NOTE: don't change mount locations, these are embedded in the 'in.pkl' file

if [ ! -f "$1" ]; then
    echo "in-file does not exist: $1"
fi

docker run --network="host" --rm -i \
    --shm-size=6gb \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd \
    --mount type=bind,source=$(dirname $1),target=/local/pkls \
    --env PY_COLORS=1 \
    $(env | grep '^SKYSCAN_' | awk '$0="--env "$0') \
    icecube/skymap_scanner:latest \
    python -m skymap_scanner.client.reco_pixel_pkl \
    --in-pkl /local/pkls/$(basename $1) \
    --out-pkl /local/pkls/out.pkl \
    --log DEBUG