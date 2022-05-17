#!/bin/sh

set -x

docker run --network="host" --rm -i \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    --env PY_COLORS=1 \
    $1 skymap_scanner.client.scan_pixel \
    --in-file $SKYSCAN_CLIENT_SCANNER_IN_FILE \
    --out-file $SKYSCAN_CLIENT_SCANNER_OUT_FILE \
    --log DEBUG