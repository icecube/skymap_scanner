#!/bin/bash

########################################################################
#
# Wait for startup.json after launching a Skymap Scanner server
# and before launching any clients
#
# Pass in one argument, the directory that will contain the startup.json
#
########################################################################

waitsec="5"
timeout=${WAIT_FOR_STARTUP_JSON:-"10 minutes"}
echo "Will wait for startup.json for $timeout in $waitsec second intervals"

if [ -z "$1" ]; then
    echo "Usage: wait_for_startup_json.sh STARTUP_DIRECTORY"
    exit 1
fi
if [ ! -d "$1" ]; then
    echo "Directory Not Found: $1"
    exit 2
fi

# wait until the startup.json file exists (with a timeout)
endtime=$(date -ud "$timeout" +%s)  # wait this long for server startup
while [[ $(date -u +%s) -le $endtime ]]; do
    if [[ -e "$1/startup.json" ]]; then
        echo "Success! 'startup.json' file found:"
        ls $1
        exit 0  # Done!
    fi
    echo "waiting for 'startup.json' ($waitsec second intervals)..."
    sleep $waitsec
done

echo "Failed. 'startup.json' not found within time limit ($timeout):"
ls $1
exit 62  # Timer expired