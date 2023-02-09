#!/bin/bash

########################################################################
#
# Wait for $1 after launching a Skymap Scanner server
# and before launching any clients
#
# Pass in one argument, the filepath to the file
#
########################################################################

waitsec="5"
timeout=${CLIENT_STARTER_WAIT_FOR_STARTUP_JSON:-"600"}
echo "Will wait for '$1' for $timeout seconds in $waitsec second intervals"

if [ -z "$1" ]; then
    echo "Usage: wait_for_startup_json.sh STARTUP_JSON_FILE"
    exit 1
fi
if [ ! -d $(dirname $1) ]; then
    echo "Directory Not Found: $(dirname $1)"
    exit 2
fi

# wait until the startup-json file exists (with a timeout)
endtime=$(date -ud "$timeout seconds" +%s)  # wait this long for server startup
while [[ $(date -u +%s) -le $endtime ]]; do
    if [[ -e "$1" ]]; then
        echo "Success! '$1' file found:"
        ls $1
        exit 0  # Done!
    fi
    echo "waiting for '$1' ($waitsec second intervals)..."
    sleep $waitsec
done

echo "Failed. '$1' not found within time limit ($timeout seconds):"
ls $1
exit 62  # Timer expired