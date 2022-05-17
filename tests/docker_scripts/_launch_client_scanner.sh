#!/bin/sh

set -x

docker run --network="host" --rm -i \
    --mount type=bind,source=$SKYSCAN_GCD_DIR,target=/local/gcd-dir \
    --mount type=bind,source=$SKYSCAN_CLIENT_SCANNER_FILES_DIR,target=/local/in-out-files \
    --env PY_COLORS=1 \
    $1 skymap_scanner.client.scan_pixel \
    --in-file /local/in-out-files/$SKYSCAN_CLIENT_SCANNER_IN_FILENAME \
    --out-file /local/in-out-files/$SKYSCAN_CLIENT_SCANNER_OUT_FILENAME \
    --log DEBUG