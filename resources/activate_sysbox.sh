#!/bin/bash
set -euo pipefail

# install and activate sysbox runtime for docker-in-docker

docker --version

# Skip if already installed & active
if systemctl is-active --quiet sysbox; then
    echo "sysbox already active"
    exit 0
fi

temp_dir="$(mktemp -d)" && cd "$temp_dir"

# Clean out any containers that might block Docker restart
docker rm $(docker ps -aq) -f || echo "ok: no docker containers to remove"

# Install prerequisites and Sysbox
sudo apt-get update -y
sudo apt-get install -y jq wget
wget https://downloads.nestybox.com/sysbox/releases/v0.6.4/sysbox-ce_0.6.4-0.linux_amd64.deb
sudo apt-get install -y ./sysbox-ce_0.6.4-0.linux_amd64.deb

# Sanity checks
sudo systemctl status sysbox -n20 || (sudo journalctl -u sysbox -n200; false)
docker info | jq '.Runtimes | keys' | tee /dev/stderr | grep -q '"sysbox-runc"' \
  || (echo "::error::Docker runtime 'sysbox-runc' not registered"; docker info; false)
