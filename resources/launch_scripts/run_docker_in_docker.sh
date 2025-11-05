#!/bin/bash
set -euo pipefail
set -ex

########################################################################
#
# Docker-in-Docker helper
#
# - Saves DIND_INNER_IMAGE to a compressed tarball (shared, lock-protected)
# - Mounts host dirs for inner Docker (/var/lib/docker and temp)
# - Forwards selected env vars into the outer container
# - Mounts specified RO/RW paths
# - Loads the inner image inside the outer container and runs DIND_OUTER_CMD
#
# Required env:
#   DIND_OUTER_IMAGE            - image to run as the outer (DIND) container
#   DIND_INNER_IMAGE            - image that must be available inside the outer container
#   DIND_NETWORK                - docker network name for the outer container
#   DIND_FORWARD_ENV_PREFIXES   - space-separated prefixes to forward (e.g., "EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_")
#   DIND_FORWARD_ENV_VARS       - space-separated exact var names to forward
#   DIND_BIND_RO_DIRS           - space-separated host dirs to bind read-only at same path
#   DIND_BIND_RW_DIRS           - space-separated host dirs to bind read-write at same path
#   DIND_OUTER_CMD              - command run inside outer container AFTER docker load
#
# Cache/tuning (optional):
#   DIND_CACHE_ROOT             - where to store tarballs (default: "$HOME/.cache/dind")
#   DIND_HOST_BASE              - base for inner Docker storage (default: "${RUNNER_TEMP:-/tmp}/dind-$(uuidgen)")
#   DIND_IMAGE_TAR_NAME         - override name of tarball (default derived from DIND_INNER_IMAGE)
#   DIND_EXTRA_ARGS             - extra args appended to `docker run` (string, optional)
#
########################################################################

########################################################################
# Validate required inputs
########################################################################
if [[ -z "${DIND_OUTER_IMAGE:-}" ]]; then
    echo "::error::'DIND_OUTER_IMAGE' must be set."
    exit 1
fi
if [[ -z "${DIND_INNER_IMAGE:-}" ]]; then
    echo "::error::'DIND_INNER_IMAGE' must be set."
    exit 1
fi
if [[ -z "${DIND_NETWORK:-}" ]]; then
    echo "::error::'DIND_NETWORK' must be set."
    exit 1
fi
if [[ -z "${DIND_FORWARD_ENV_PREFIXES:-}" ]]; then
    echo "::error::'DIND_FORWARD_ENV_PREFIXES' must be set (space-separated list of prefixes)."
    exit 1
fi
if [[ -z "${DIND_FORWARD_ENV_VARS:-}" ]]; then
    echo "::error::'DIND_FORWARD_ENV_VARS' must be set (space-separated list of exact var names)."
    exit 1
fi
if [[ -z "${DIND_BIND_RO_DIRS:-}" ]]; then
    echo "::error::'DIND_BIND_RO_DIRS' must be set (space-separated list of host dirs)."
    exit 1
fi
if [[ -z "${DIND_BIND_RW_DIRS:-}" ]]; then
    echo "::error::'DIND_BIND_RW_DIRS' must be set (space-separated list of host dirs)."
    exit 1
fi
if [[ -z "${DIND_OUTER_CMD:-}" ]]; then
    echo "::error::'DIND_OUTER_CMD' must be set (command to run inside the outer container)."
    exit 1
fi

########################################################################
# Ensure Sysbox runtime is active (required for Docker-in-Docker)
########################################################################
if [[ "${_CI_SCANNER_CONTAINER_PLATFORM:-}" != "docker" ]]; then
    echo "::error::Sysbox is only required for docker -- don't run this check"
    exit 1
fi

if ! systemctl is-active --quiet sysbox; then
    echo "::error::Sysbox runtime is required for Docker-in-Docker but is not active."
    echo "Install via: https://github.com/nestybox/sysbox -- or see ewms-pilot docs for recommendations"
    exit 1
else
    echo "Sysbox runtime (required for Docker-in-Docker) is active."
fi


########################################################################
# Cache root (optional, with default)
########################################################################
if [[ -z "${DIND_CACHE_ROOT:-}" ]]; then
    DIND_CACHE_ROOT="$HOME/.cache/dind"
fi
mkdir -p "$DIND_CACHE_ROOT"

########################################################################
# Derive a filesystem-safe tarball name from DIND_INNER_IMAGE if not provided
########################################################################
if [[ -z "${DIND_IMAGE_TAR_NAME:-}" ]]; then
    # ex: "icecube/skymap_scanner:local" -> "icecube-skymap_scanner-local.tar.gz"
    safe_name="$(echo "$DIND_INNER_IMAGE" | tr '/:' '--')"
    DIND_IMAGE_TAR_NAME="${safe_name}.tar.gz"
fi

saved_images_dir="$DIND_CACHE_ROOT/saved-images"
mkdir -p "$saved_images_dir"
inner_tar_gz="$saved_images_dir/$DIND_IMAGE_TAR_NAME"
lockfile="$inner_tar_gz.lock"

########################################################################
# Create compressed inner-image tarball (shared, lock-protected)
########################################################################
if [[ ! -s "$inner_tar_gz" ]]; then
    exec {lockfd}> "$lockfile"
    flock "$lockfd"
    if [[ ! -s "$inner_tar_gz" ]]; then
        tmp_gz="$(mktemp "$inner_tar_gz.XXXXXX")"
        # Verify image exists locally
        docker image inspect "$DIND_INNER_IMAGE" >/dev/null
        if command -v pigz >/dev/null 2>&1; then
            docker save "$DIND_INNER_IMAGE" | pigz -1 > "$tmp_gz"
        else
            docker save "$DIND_INNER_IMAGE" | gzip -1 > "$tmp_gz"
        fi
        mv -f "$tmp_gz" "$inner_tar_gz"
    fi
    flock -u "$lockfd"
    rm -f "$lockfile" || true
fi

########################################################################
# Prepare host dirs for inner Docker writable layers & temp
########################################################################
if [[ -z "${DIND_HOST_BASE:-}" ]]; then
    if [[ -n "${RUNNER_TEMP:-}" ]]; then
        DIND_HOST_BASE="$RUNNER_TEMP/dind-$(uuidgen)"
    else
        DIND_HOST_BASE="/tmp/dind-$(uuidgen)"
    fi
fi
inner_docker_root="$DIND_HOST_BASE/lib"
inner_docker_tmp="$DIND_HOST_BASE/tmp"
mkdir -p "$inner_docker_root" "$inner_docker_tmp"

########################################################################
# Run outer container: load inner image, then exec DIND_OUTER_CMD
########################################################################
# shellcheck disable=SC2046
docker run --rm --privileged \
    --network="$DIND_NETWORK" \
    \
    -v "$saved_images_dir:/saved-images:ro" \
    \
    -v "$inner_docker_root:/var/lib/docker" \
    -v "$inner_docker_tmp:$inner_docker_tmp" \
    -e DOCKER_TMPDIR="$inner_docker_tmp" \
    \
    $( \
        for d in $DIND_BIND_RO_DIRS; do \
            echo -n " -v $d:$d:ro"; \
        done \
    ) \
    $( \
        for d in $DIND_BIND_RW_DIRS; do \
            echo -n " -v $d:$d"; \
        done \
    ) \
    \
    $( \
        regex="$(echo "$DIND_FORWARD_ENV_PREFIXES" | sed 's/ \+/|/g')"; \
        env | grep -E "^(${regex})" | cut -d'=' -f1 | sed 's/^/--env /' | tr '\n' ' ' \
    ) \
    \
    $( \
        for k in $DIND_FORWARD_ENV_VARS; do \
            env | grep -q "^$k=" && echo -n " --env $k"; \
        done \
    ) \
    \
    $( [[ -n "${DIND_EXTRA_ARGS:-}" ]] && echo "$DIND_EXTRA_ARGS" ) \
    \
    "$DIND_OUTER_IMAGE" /bin/bash -lc "\
        docker load -i /saved-images/$(basename "$inner_tar_gz") && \
        $DIND_OUTER_CMD \
    "
