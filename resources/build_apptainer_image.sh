#!/bin/bash
set -euo pipefail
echo "now: $(date -u +"%Y-%m-%dT%H:%M:%S.%3N")"

########################################################################
# Require environment variables
########################################################################
if [[ -z "${CI_DOCKER_IMAGE_TAG:-}" ]]; then
    echo "::error:: CI_DOCKER_IMAGE_TAG must be set"
    exit 1
fi
if [[ -z "${APPTAINER_CACHEDIR:-}" ]]; then
    echo "::error:: APPTAINER_CACHEDIR must be set"
    exit 1
fi

APPTAINER_SANDBOX_DIR="skymap_scanner.sandbox"

########################################################################
# Build sandbox image
########################################################################
echo "building apptainer sandbox at: ${APPTAINER_SANDBOX_DIR}"
# ensure a clean target (apptainer refuses to overwrite without --force)
rm -rf "${APPTAINER_SANDBOX_DIR}" || true
apptainer build --sandbox --force "${APPTAINER_SANDBOX_DIR}" docker-daemon://"$CI_DOCKER_IMAGE_TAG"
du -sh "${APPTAINER_SANDBOX_DIR}" || ls -lh "${APPTAINER_SANDBOX_DIR}"

########################################################################
# Drop apptainer caches
########################################################################
echo "clearing apptainer caches..."
du -sh "$APPTAINER_CACHEDIR" || true
rm -rf "$APPTAINER_CACHEDIR" || true

########################################################################
# Free docker stuff now that sandbox is built
########################################################################
echo "clearing docker things..."
BEFORE="$(df -B1 --output=avail / | tail -1)"

# -- docker layers
docker ps -a --filter "ancestor=$CI_DOCKER_IMAGE_TAG" -q | xargs -r docker rm -f
docker rmi -f "$CI_DOCKER_IMAGE_TAG" || true

# -- prune buildkit + volume
docker ps -aq --filter "label=name=buildx_buildkit" | xargs -r docker rm -f || true
docker ps -aq --filter "ancestor=moby/buildkit:buildx-stable-1" | xargs -r docker rm -f || true
docker buildx ls | awk 'NR>1{gsub(/\*$/,"",$1); if($1!="default" && $1!="") print $1}' | xargs -r -n1 docker buildx rm -f || true
docker builder prune -af || true
docker system prune -af --volumes || true
docker volume ls -q --filter 'name=buildx_buildkit_.*_state' | xargs -r docker volume rm -f || true

# -- report
AFTER="$(df -B1 --output=avail / | tail -1)"
DELTA="$((AFTER - BEFORE))"
GIB="$(awk -v b="$DELTA" 'BEGIN{printf "%.2f", b/1024/1024/1024}')"
MIB="$(awk -v b="$DELTA" 'BEGIN{printf "%.0f", b/1024/1024}')"
echo "Freed: ${GIB} GiB (${MIB} MiB)"
