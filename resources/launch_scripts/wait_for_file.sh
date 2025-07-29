#!/bin/bash
set -euo pipefail
set -ex

########################################################################
#
# Wait for $1 after launching a Skymap Scanner server
# and before launching any workers
#
# Pass in two arguments, the filepath to the file & wait duration
#
########################################################################

if [ -z "${1-}" ] || [ -z "${2-}" ]; then
    echo "Usage: wait_for_file.sh FILE DURATION_SECONDS"
    exit 1
fi
if [ ! -d $(dirname $1) ]; then
    echo "Directory Not Found: $(dirname $1)"
    exit 2
fi
if [[ $2 != +([[:digit:]]) ]]; then
    echo "Wait duration must be a number (seconds): $2"
    exit 2
fi

waitsec="5"
timeout="$2"
echo "Will wait for '$1' for $timeout seconds in $waitsec second intervals"

# wait until the file exists (with a timeout)
endtime=$(date -ud "$timeout seconds" +%s) # wait this long
while [[ $(date -u +%s) -le $endtime ]]; do
    if [[ -e $1 ]]; then
        echo "Success! '$1' file found:"
        ls $1
        exit 0 # Done!
    fi
    echo "waiting for '$1' ($waitsec second intervals)..."
    sleep $waitsec
done

echo "Failed. '$1' not found within time limit ($timeout seconds):"
ls $1
exit 62 # Timer expired
