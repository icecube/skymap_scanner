#!/bin/bash

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "ERROR: Missing dirpath(s) (usage: reconfigure-rabbitmq.sh SRC_DIRPATH DEST_DIRPATH)"
    exit 1

CUSTOM_CONF="$1/custom.conf"

sudo bash -c "\n## Custom\n' >> $CUSTOM_CONF"
sudo bash -c "echo -e 'log.console.level = debug\n' >> $CUSTOM_CONF"
sudo bash -c "echo -e 'loopback_users = none\n' >> $CUSTOM_CONF"  # allows guest/guest from non-localhost

# refresh rabbitmq config - based on ENTRYPOINT logic
docker exec rabbitmq bash -c "cat $2/custom.conf >> /opt/bitnami/rabbitmq/etc/rabbitmq/rabbitmq.conf"

# sleep to prevent interleaved output in GHA logs
docker exec rabbitmq cat /opt/bitnami/rabbitmq/etc/rabbitmq/rabbitmq.conf && sleep 1

echo
echo "restarting rabbitmq container"
docker restart rabbitmq

# wait for rabbitmq container to restart
until [ "$(docker inspect -f {{.State.Running}} rabbitmq)" == "true" ]; do
    sleep 0.1
done
