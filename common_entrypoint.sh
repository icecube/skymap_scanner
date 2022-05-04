#!/bin/sh

set -x

if [ -z "$1" ]; then
	echo "ERROR: no mode was given (\$1 is empty)"
	exit 1
fi

python -m $@