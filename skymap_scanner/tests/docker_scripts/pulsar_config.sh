#!/bin/sh

# From the README.md

set -x

# make sure the ports are active
export DOCKERIZE_VERSION=v0.3.0
wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz && sudo tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz
dockerize -wait tcp://localhost:8080 -timeout 1m
dockerize -wait tcp://localhost:6650 -timeout 1m

docker exec -i $1 bin/pulsar-admin tenants create icecube
docker exec -i $1 bin/pulsar-admin namespaces create icecube/skymap
docker exec -i $1 bin/pulsar-admin namespaces set-deduplication icecube/skymap --enable
docker exec -i $1 bin/pulsar-admin namespaces create icecube/skymap_metadata
docker exec -i $1 bin/pulsar-admin namespaces set-deduplication icecube/skymap_metadata --enable
docker exec -i $1 bin/pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1

docker exec -i $1 bin/pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/to_be_scanned --partitions 6
docker exec -i $1 bin/pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/scanned --partitions 6
