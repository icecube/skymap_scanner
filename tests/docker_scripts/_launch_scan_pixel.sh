#!/bin/sh

set -x

# NOTE: don't change mount locations, these are embedded in the 'in.pkl' file

docker run --network="host" --pull=always --rm -i \
    --shm-size=6gb \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    --mount type=bind,source="$(pwd)"/$SKYSCAN_CLIENT_SCANNER_FILES_DIR,target=/local/$SKYSCAN_CLIENT_SCANNER_FILES_DIR \
    --env PY_COLORS=1 \
    icecube/skymap_scanner:latest \
    python -m skymap_scanner.client.scan_pixel_pkl \
    --in-file /local/$SKYSCAN_CLIENT_SCANNER_FILES_DIR/$SKYSCAN_CLIENT_SCANNER_IN_FILENAME \
    --out-file /local/$SKYSCAN_CLIENT_SCANNER_FILES_DIR/$SKYSCAN_CLIENT_SCANNER_OUT_FILENAME \
    --log DEBUG