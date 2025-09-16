#!/bin/bash
set -euo pipefail; echo "now: $(date -u +"%Y-%m-%dT%H:%M:%S.%3N")"
set -x

# https://github.com/apptainer/apptainer/blob/main/INSTALL.md#installing-apptainer
# Ensure repositories are up-to-date
sudo apt-get update
# Install debian packages for dependencies
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
# Clone the repo
git clone https://github.com/apptainer/apptainer.git
cd apptainer
git checkout v1.3.2
# Compiling Apptainer
./mconfig
cd $(/bin/pwd)/builddir
make
sudo make install
apptainer --version

# https://github.com/apptainer/apptainer/blob/main/INSTALL.md#apparmor-profile-ubuntu-2310
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

# Install squashfuse in order to run .sif
#   without squashfuse, .sif can't be run directly and needs to be converted
#   to a sandbox dir, 1 for each instance
sudo apt-get update
sudo apt-get install -y squashfuse
