#!/bin/sh

set -x

cd skymap_scanner/
cp -r -n ../cloud_tools/* .
docker build --no-cache -t $1 .