#!/bin/bash
set -euo pipefail
set -ex

########################################################################
#
# Docker-in-Docker helper — see echo-block below for details
#
########################################################################

echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                           ║"
echo "║             Docker-in-Docker Helper — Runtime Environment Info            ║"
echo "║                                                                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Purpose:     Launch a privileged outer Docker container that hosts an    ║"
echo "║               inner Docker daemon.                                        ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Details:                                                                 ║"
echo "║   - Saves DIND_INNER_IMAGE to a tarball on host (lock-protected)          ║"
echo "║   - Mounts host dirs for inner Docker (/var/lib/docker and temp)          ║"
echo "║   - Forwards selected env vars into the outer container                   ║"
echo "║   - Mounts specified RO/RW paths                                          ║"
echo "║   - Loads inner image inside outer container, then runs DIND_OUTER_CMD    ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Host System Info:                                                        ║"
echo "║    - Host:      $(hostname)                                               ║"
echo "║    - User:      $(whoami)                                                 ║"
echo "║    - Kernel:    $(uname -r)                                               ║"
echo "║    - Platform:  $(uname -s) $(uname -m)                                   ║"
echo "║    - Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")                      ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Environment Variables:                                                   ║"

print_env_var() {
    local var="$1"
    local is_required="${2:-false}"
    local desc="${3:-}"
    local val="${!var:-}"

    # Fail early for missing required vars
    if [[ "$is_required" == "true" && -z "$val" ]]; then
        echo "::error::'$var' must be set${desc:+ ($desc)}."
        exit 1
    fi

    # Print nicely formatted entry
    echo "║    - ${var}="
    if [[ -n "$val" ]]; then
        echo "║        ${val}"
    else
        echo "║        <unset>"
    fi

    if [[ "$is_required" == "true" ]]; then
        echo "║        (required) ${desc}"
    else
        echo "║        (optional) ${desc}"
    fi
}

print_env_var DIND_OUTER_IMAGE          true  "image to run as the outer (DIND) container"
print_env_var DIND_INNER_IMAGE          true  "image that must be available inside the outer container"
print_env_var DIND_NETWORK              true  "docker network name for the outer container"
print_env_var DIND_FORWARD_ENV_PREFIXES true  "space-separated prefixes to forward"
print_env_var DIND_FORWARD_ENV_VARS     true  "space-separated exact var names to forward"
print_env_var DIND_BIND_RO_DIRS         true  "space-separated host dirs to bind read-only at same path"
print_env_var DIND_BIND_RW_DIRS         true  "space-separated host dirs to bind read-write at same path"
print_env_var DIND_OUTER_CMD            true  "command run inside outer container AFTER docker load"

print_env_var DIND_CACHE_ROOT           false "path to store tarballs (default: ~/.cache/dind)"
print_env_var DIND_HOST_BASE            false "base path for inner Docker storage"
print_env_var DIND_IMAGE_TAR_NAME       false "override tarball filename"
print_env_var DIND_EXTRA_ARGS           false "extra args appended to docker run"

echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo

########################################################################
# Ensure Sysbox runtime is active (required for Docker-in-Docker)
########################################################################
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
    "$DIND_OUTER_IMAGE" /bin/bash -c "\
        docker load -i /saved-images/$(basename "$inner_tar_gz") && \
        $DIND_OUTER_CMD \
    "
