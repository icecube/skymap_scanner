#!/bin/bash
eval `/cvmfs/icecube.opensciencegrid.org/py3-v4.1.0/setup.sh`
#/cvmfs/icecube.opensciencegrid.org/users/steinrob/combo-realtime/build/env-shell.sh
ENV_PATH=$1
$ENV_PATH/env-shell.sh python $ENV_PATH/skymap_scanner/resources/scripts/alert_v2_listener.py "${@:2}"
