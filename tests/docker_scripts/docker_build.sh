#!/bin/sh

set -x

docker build --no-cache -t $1 .