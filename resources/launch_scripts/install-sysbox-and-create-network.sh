#!/bin/bash
set -euo pipefail

########################################################################
# Sysbox Setup + Docker Network Initialization
#
# - Installs Sysbox CE, if not already installed
# - Verifies Sysbox is running and active
# - Creates a Docker network for use with Docker-in-Docker setups
#
# Usage:
#   ./install-sysbox-and-create-network.sh <docker_network_name>
#
# Example:
#   ./install-sysbox-and-create-network.sh ci-dind-net
########################################################################

if [[ $# -ne 1 ]]; then
    echo "::error::Usage: $0 <docker_network_name>"
    exit 1
else
    DOCKER_NETWORK_NAME="$1"
fi

########################################################################
# Intro banner
########################################################################
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
_ECHO_HEADER="║        Sysbox Setup and Docker Network Utility — WIPAC Developers         ║"
echo "$_ECHO_HEADER"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Host Info:                                                               ║"
echo "║    - Hostname:  $(hostname)                                               ║"
echo "║    - User:      $(whoami)                                                 ║"
echo "║    - Kernel:    $(uname -r)                                               ║"
echo "║    - Platform:  $(uname -s) $(uname -m)                                   ║"
echo "║    - Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")                      ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Target Docker Network: $DOCKER_NETWORK_NAME                              ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo

########################################################################
# Section 1 — Print system & Docker info
########################################################################
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                      Checking Docker Installation...                      ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
docker --version
echo "Docker CLI check complete."

########################################################################
# Section 2 — Install Sysbox (if missing)
########################################################################
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                       Installing Sysbox Runtime...                        ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
if ! command -v sysbox-runc >/dev/null 2>&1; then
    echo "Sysbox not found — installing..."
    temp_dir=$(mktemp -d)
    cd "$temp_dir"

    wget https://downloads.nestybox.com/sysbox/releases/v0.6.4/sysbox-ce_0.6.4-0.linux_amd64.deb
    docker rm $(docker ps -a -q) -f || echo "ok: no docker containers to remove"
    sudo apt-get update
    sudo apt-get install -y jq ./sysbox-ce_0.6.4-0.linux_amd64.deb
else
    echo "Sysbox runtime already installed."
fi
echo "Sysbox installation step complete."

########################################################################
# Section 3 — Verify Sysbox service
########################################################################
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                        Verifying Sysbox Service...                        ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
if ! systemctl is-active --quiet sysbox; then
    echo "::error::Sysbox could not be activated."
    sudo systemctl status sysbox -n20 || true
    exit 1
else
    echo "Sysbox runtime (required for Docker-in-Docker) is active."
    sudo systemctl status sysbox -n20
fi
echo "Sysbox verification step complete."

########################################################################
# Section 4 — Create Docker network
########################################################################
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                        Creating Docker Network...                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
if ! docker network inspect "$DOCKER_NETWORK_NAME" >/dev/null 2>&1; then
    echo "Creating docker network: $DOCKER_NETWORK_NAME"
    docker network create "$DOCKER_NETWORK_NAME"
    echo "Docker network created successfully."
else
    echo "Docker network already exists: $DOCKER_NETWORK_NAME"
fi

########################################################################
# Final summary
########################################################################
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                              Setup Complete.                              ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Sysbox runtime: active                                                   ║"
echo "║  Docker version: $(docker --version | head -n1)                           ║"
echo "║  Network: $DOCKER_NETWORK_NAME                                            ║"
echo "║  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")                          ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo
