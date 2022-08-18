#!/bin/bash

########################################################################
#
# Wait for all startup files after launching a Skymap Scanner server
# and before launching any clients
#
# Pass in one argument, the directory that will contain the startup files
#
########################################################################

if [ -z "$1" ]; then
    echo "Usage: wait_for_startup_files.sh STARTUP_DIRECTORY"
    exit 1
fi
if [ ! -d "$1" ]; then
    echo "Directory Not Found: $1"
    exit 2
fi

# wait until the mq-basename.txt file exists (with a timeout)
waitsec="5"
timeout="10 minutes"
endtime=$(date -ud "$timeout" +%s)  # wait this long for server startup
while [[ $(date -u +%s) -le $endtime ]]; do
    if [[ -e "$1/mq-basename.txt" && -e "$1/baseline_GCD_file.txt" && -e "$1/GCDQp_packet.pkl" ]]; then
        echo "Success! All startup files found:"
        ls $1
        exit 0  # Done!
    fi
    echo "waiting for startup files ($waitsec second intervals)..."
    sleep $waitsec
done

echo "Failed. Not all startup files found within time limit ($timeout):"
ls $1
exit 62  # Timer expired