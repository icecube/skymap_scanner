#!/bin/bash
set -ex

########################################################################
#
# Runs a rabbitmq broker server (in background)
#
########################################################################

mkdir -p ./local-broker/
cd ./local-broker/

if [ ! -f "docker-rabbitmq.sh" ]; then
    wget raw.githubusercontent.com/Observation-Management-Service/MQClient/master/resources/rabbitmq-custom.conf
    wget raw.githubusercontent.com/Observation-Management-Service/MQClient/master/resources/docker-rabbitmq.sh
fi

./docker-rabbitmq.sh local-rabbitmq  # runs docker container in background
