#!/bin/sh

set -x

cd skymap_scanner/
docker build --no-cache -t $1 .