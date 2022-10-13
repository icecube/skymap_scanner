#!/bin/bash

########################################################################
#
# Launch the Skymap Scanner server
#
# Pass in the arguments as if this were just the python sub-module
#
########################################################################

ARGS="$*" # all of the arguments stuck together into a single string

set -x


# Figure where to get image
IMAGE="docker://icecube/skymap_scanner"
if [ "$LOOK_FOR_LOCAL_IMAGE" == "1" ]; then
    SIF_FILE="${SKYSCAN_SIF_FILE:=skymap_scanner.sif}"
    if [ ! -e $SIF_FILE ]; then
        if [ ! -w $(dirname $SIF_FILE) ]; then
            echo "ERROR: $SIF_FILE does not exist and $(dirname $SIF_FILE) is not writable"
            SIF_FILE='skymap_scanner.sif'
        fi
        echo "Building $(basename $SIF_FILE) in $(pwd)"
        sudo singularity build $SIF_FILE docker://icecube/skymap_scanner
    fi
    echo "Using $SIF_FILE"
    ls -lhd $SIF_FILE
    IMAGE="$SIF_FILE"
fi


# Run
singularity run $IMAGE python -m skymap_scanner.server $ARGS