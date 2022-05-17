#!/bin/sh

set -x

if [ -z "$1" ]; then
	echo "ERROR: no skymap_scanner sub-package/module was given (\$1 is empty)"
	exit 1
fi

python -m $@