#!/bin/sh

set -x

docker run -i -d --rm \
    -p 6650:6650 \
    -p 8080:8080 \
    --name $1 apachepulsar/pulsar:2.6.0 /bin/bash \
    -c "sed -i s/brokerDeleteInactiveTopicsEnabled=.*/brokerDeleteInactiveTopicsEnabled=false/ /pulsar/conf/standalone.conf && bin/pulsar standalone"