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
#   DIND_OUTER_IMAGE          - image to run as the outer (DIND) container
#   DIND_INNER_IMAGE          - image that must be available inside the outer container
#
# Recommended env:
#   DIND_NETWORK              - docker network name for the outer container (optional)
#   DIND_FORWARD_ENV_PREFIXES - space-separated prefixes to forward (default: "EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_")
#   DIND_FORWARD_ENV_VARS     - space-separated exact var names to forward (optional)
#   DIND_BIND_RO_DIRS         - space-separated host dirs to bind read-only at same path (optional)
#   DIND_BIND_RW_DIRS         - space-separated host dirs to bind read-write at same path (optional)
#   DIND_OUTER_CMD            - command run inside outer container AFTER docker load (default: "bash")
#
# Cache/tuning (optional):
#   DIND_CACHE_ROOT           - where to store tarballs (default: "$HOME/.cache/dind")
#   DIND_HOST_BASE            - base for inner Docker storage (default: "${RUNNER_TEMP:-/tmp}/dind-$(uuidgen)")
#   DIND_IMAGE_TAR_NAME       - override name of tarball (default derived from DIND_INNER_IMAGE)
#
########################################################################

########################################################################
# Validate inputs
########################################################################
if [[ -z "${DIND_OUTER_IMAGE:-}" ]]; then
    echo "::error::'DIND_OUTER_IMAGE' must be set."
    exit 1
fi
if [[ -z "${DIND_INNER_IMAGE:-}" ]]; then
    echo "::error::'DIND_INNER_IMAGE' must be set."
    exit 1
fi

if [[ -z "${DIND_FORWARD_ENV_PREFIXES:-}" ]]; then
    DIND_FORWARD_ENV_PREFIXES="EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_"
fi

if [[ -z "${DIND_CACHE_ROOT:-}" ]]; then
    DIND_CACHE_ROOT="$HOME/.cache/dind"
fi
mkdir -p "$DIND_CACHE_ROOT"

# Derive a filesystem-safe tarball name from DIND_INNER_IMAGE if not provided
if [[ -z "${DIND_IMAGE_TAR_NAME:-}" ]]; then
    # ex: "icecube/skymap_scanner:local" -> "icecube-skymap_scanner-local.tar.gz"
    safe_name="$(echo "$INNER_IMAGE" | tr '/:' '--')"
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
        docker image inspect "$INNER_IMAGE" >/dev/null
        if command -v pigz >/dev/null 2>&1; then
            docker save "$INNER_IMAGE" | pigz -1 > "$tmp_gz"
        else
            docker save "$INNER_IMAGE" | gzip -1 > "$tmp_gz"
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

# Outer command default
if [[ -z "${DIND_OUTER_CMD:-}" ]]; then
    DIND_OUTER_CMD="bash"
fi

########################################################################
# Run outer container: load inner image, then exec DIND_OUTER_CMD
########################################################################
# shellcheck disable=SC2046
docker run --rm \
    \
    --privileged \
    $( [[ -n "${DIND_NETWORK:-}" ]] && echo "--network=$DIND_NETWORK" ) \
    \
    -v "$saved_images_dir:/saved-images:ro" \
    \
    -v "$inner_docker_root:/var/lib/docker" \
    -v "$inner_docker_tmp:$inner_docker_tmp" \
    -e DOCKER_TMPDIR="$inner_docker_tmp" \
    \
    $( if [[ -n "${DIND_BIND_RO_DIRS:-}" ]]; then for d in $BIND_RO_DIRS; do echo -n " -v $d:$d:ro"; done; fi ) \
    $( if [[ -n "${DIND_BIND_RW_DIRS:-}" ]]; then for d in $BIND_RW_DIRS; do echo -n " -v $d:$d"; done; fi ) \
    \
    $( \
        if [[ -n "${DIND_FORWARD_ENV_PREFIXES:-}" ]]; then \
            regex="$(echo "$FORWARD_ENV_PREFIXES" | sed 's/ \+/|/g')"; \
            env | grep -E "^(${regex})" | cut -d'=' -f1 | sed 's/^/--env /' | tr '\n' ' '; \
        fi \
    ) \
    \
    $( \
        if [[ -n "${DIND_FORWARD_ENV_VARS:-}" ]]; then \
            for k in $FORWARD_ENV_VARS; do \
                env | grep -q "^$k=" && echo -n " --env $k"; \
            done; \
        fi \
    ) \
    \
    $( [[ -n "${DIND_EXTRA_ARGS:-}" ]] && echo "$DIND_EXTRA_ARGS" ) \
    \
    "$OUTER_IMAGE" /bin/bash -lc "\
        docker load -i /saved-images/$(basename "$inner_tar_gz") && \
        exec $OUTER_CMD \
    "
