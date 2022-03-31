#!/bin/sh

# From the README.md

docker exec -ti $1 bin/pulsar-admin tenants create icecube
docker exec -ti $1 bin/pulsar-admin namespaces create icecube/skymap
docker exec -ti $1 bin/pulsar-admin namespaces set-deduplication icecube/skymap --enable
docker exec -ti $1 bin/pulsar-admin namespaces create icecube/skymap_metadata
docker exec -ti $1 bin/pulsar-admin namespaces set-deduplication icecube/skymap_metadata --enable
docker exec -ti $1 bin/pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1

docker exec -ti $1 bin/pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/to_be_scanned --partitions 6
docker exec -ti $1 bin/pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/scanned --partitions 6
