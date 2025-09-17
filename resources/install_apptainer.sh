#!/bin/bash
set -euo pipefail
echo "now: $(date -u +"%Y-%m-%dT%H:%M:%S.%3N")"
set -x

########################################################################
# Install Apptainer build dependencies
# https://github.com/apptainer/apptainer/blob/main/INSTALL.md#installing-apptainer
########################################################################
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    libseccomp-dev \
    pkg-config \
    uidmap \
    squashfs-tools \
    fakeroot \
    cryptsetup \
    tzdata \
    dh-apparmor \
    curl wget git

########################################################################
# Clone and build Apptainer
########################################################################
git clone https://github.com/apptainer/apptainer.git
cd apptainer
git checkout v1.3.2
./mconfig
cd $(/bin/pwd)/builddir
make
sudo make install
apptainer --version

########################################################################
# Add AppArmor profile (Ubuntu 23.10+)
# https://github.com/apptainer/apptainer/blob/main/INSTALL.md#apparmor-profile-ubuntu-2310
########################################################################
sudo tee /etc/apparmor.d/apptainer << 'EOF'
# Permit unprivileged user namespace creation for apptainer starter
abi <abi/4.0>,
include <tunables/global>
profile apptainer /usr/local/libexec/apptainer/bin/starter{,-suid}
    flags=(unconfined) {
        userns,
        # Site-specific additions and overrides. See local/README for details.
        include if exists <local/apptainer>
    }
EOF
sudo systemctl reload apparmor

########################################################################
# Install squashfuse (required for running .sif directly)
########################################################################
sudo apt-get update
sudo apt-get install -y squashfuse
