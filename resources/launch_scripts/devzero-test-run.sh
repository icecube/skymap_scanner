#!/bin/bash
set -ex

########################################################################
#
# Runs a scanner instance & broker for DevZero testing
#
########################################################################


if [[ $(basename `pwd`) != "launch_scripts" ]]; then
    echo "script must be executed within 'resources/launch_scripts' directory"
    exit 1
fi


source ../../tests/env-vars.sh

export _RECO_ALGO=dummy
export _EVENTS_FILE=$(realpath "../../tests/data/realtime_events/hese_event_01.json")
export _NSIDES="1:12"

./local-scan.sh
