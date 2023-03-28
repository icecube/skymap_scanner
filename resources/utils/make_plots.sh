#!/bin/bash

########################################################################
#
# Make intermediate plots every X seconds for a scan ID
#
########################################################################

scanid=$1 # "992bac6385c046118615621bcc24c00e"
waittime=$2 # in seconds
token=$3

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: wait_for_file.sh SCAN_ID WAITSEC SKYDRIVER_TOKEN"
    exit 1
fi
if [[ "$2" != +([[:digit:]]) ]]; then
    echo "Wait duration must be a number (seconds): $2"
    exit 2
fi

while true; do
    dir="$(date +'%Y-%m-%d-%R')-$scanid"
    docker run --network="host" --rm -i --shm-size=6gb  \
        --mount type=bind,source=$(readlink -f .),target=/local \
        $(env | grep '^SKYSCAN_' | awk '$0="--env "$0') \
        icecube/skymap_scanner:local  python resources/utils/plot_skydriver_scan_result.py \
        --token $token \
        --scan-id $scanid

    mkdir $dir
    mv run* $dir
    echo "plots saved to $dir"

    echo "waiting $waittime seconds..."
    sleep $waittime
done