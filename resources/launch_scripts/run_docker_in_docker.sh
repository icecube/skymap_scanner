#!/bin/bash
set -euo pipefail
set -ex

########################################################################
#
# Docker-in-Docker helper
#
# - Saves INNER_IMAGE to a compressed tarball (shared, lock-protected)
# - Mounts host dirs for inner Docker (/var/lib/docker and temp)
# - Forwards selected env vars into the outer container
# - Mounts specified RO/RW paths
# - Loads the inner image inside the outer container and runs OUTER_CMD
#
# Required env:
#   OUTER_IMAGE              - image to run as the outer (DIND) container
#   INNER_IMAGE              - image that must be available inside the outer container
#
# Recommended env:
#   DIND_NETWORK             - docker network name for the outer container (optional)
#   FORWARD_ENV_PREFIXES     - space-separated prefixes to forward (default: "EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_")
#   FORWARD_ENV_VARS         - space-separated exact var names to forward (optional)
#   BIND_RO_DIRS             - space-separated host dirs to bind read-only at same path (optional)
#   BIND_RW_DIRS             - space-separated host dirs to bind read-write at same path (optional)
#   OUTER_CMD                - command run inside outer container AFTER docker load (default: "bash")
#
# Cache/tuning (optional):
#   DIND_CACHE_ROOT          - where to store tarballs (default: "$HOME/.cache/dind")
#   DIND_HOST_BASE           - base for inner Docker storage (default: "${RUNNER_TEMP:-/tmp}/dind-$(uuidgen)")
#   DIND_IMAGE_TAR_NAME      - override name of tarball (default derived from INNER_IMAGE)
#
########################################################################

########################################################################
# Validate inputs
########################################################################
if [[ -z "${OUTER_IMAGE:-}" ]]; then
    echo "::error::'OUTER_IMAGE' must be set."
    exit 1
fi
if [[ -z "${INNER_IMAGE:-}" ]]; then
    echo "::error::'INNER_IMAGE' must be set."
    exit 1
fi

if [[ -z "${FORWARD_ENV_PREFIXES:-}" ]]; then
    FORWARD_ENV_PREFIXES="EWMS_ _EWMS_ SKYSCAN_ _SKYSCAN_"
fi

if [[ -z "${DIND_CACHE_ROOT:-}" ]]; then
    DIND_CACHE_ROOT="$HOME/.cache/dind"
fi
mkdir -p "$DIND_CACHE_ROOT"

# Derive a filesystem-safe tarball name from INNER_IMAGE if not provided
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
        DIND_HOST_BASE="${RUNNER_TEMP}/dind-$(uuidgen)"
    else
        DIND_HOST_BASE="/tmp/dind-$(uuidgen)"
    fi
fi
inner_docker_root="$DIND_HOST_BASE/lib"
inner_docker_tmp="$DIND_HOST_BASE/tmp"
mkdir -p "$inner_docker_root" "$inner_docker_tmp"

########################################################################
# Build docker run arguments
########################################################################
args=( run --rm --privileged )
if [[ -n "${DIND_NETWORK:-}" ]]; then
    args+=( "--network=$DIND_NETWORK" )
fi
args+=( "-v" "$saved_images_dir:/saved-images:ro" )
args+=( "-v" "$inner_docker_root:/var/lib/docker" )
args+=( "-v" "$inner_docker_tmp:$inner_docker_tmp" )
args+=( "-e" "DOCKER_TMPDIR=$inner_docker_tmp" )

# Bind RO dirs at same paths
if [[ -n "${BIND_RO_DIRS:-}" ]]; then
    for d in $BIND_RO_DIRS; do
        args+=( "-v" "${d}:${d}:ro" )
    done
fi

# Bind RW dirs at same paths
if [[ -n "${BIND_RW_DIRS:-}" ]]; then
    for d in $BIND_RW_DIRS; do
        args+=( "-v" "${d}:${d}" )
    done
fi

# Forward selected env vars by prefix
if [[ -n "${FORWARD_ENV_PREFIXES:-}" ]]; then
    while IFS='=' read -r k v; do
        for p in $FORWARD_ENV_PREFIXES; do
            case "$k" in
                $p*)
                    args+=( "--env" "$k" )
                    break
                    ;;
            esac
        done
    done < <(env)
fi

# Forward explicit env vars by exact name
if [[ -n "${FORWARD_ENV_VARS:-}" ]]; then
    for k in $FORWARD_ENV_VARS; do
        if env | grep -q "^${k}="; then
            args+=( "--env" "$k" )
        fi
    done
fi

# Optional extra docker args
if [[ -n "${DIND_EXTRA_ARGS:-}" ]]; then
    # shellcheck disable=SC2206
    extra=( $DIND_EXTRA_ARGS )
    args+=( "${extra[@]}" )
fi

# Outer command
if [[ -z "${OUTER_CMD:-}" ]]; then
    OUTER_CMD="bash"
fi

########################################################################
# Run outer container: load inner image, then exec OUTER_CMD
########################################################################
docker "${args[@]}" \
    "$OUTER_IMAGE" /bin/bash -lc "\
        docker load -i /saved-images/$(basename "$inner_tar_gz") && \
        exec $OUTER_CMD \
    "
