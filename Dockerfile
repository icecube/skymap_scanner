#
# Define the base image icetray version
#
FROM icecube/icetray:icetray-devel-v1.19.1-ubuntu22.04 AS prod

# Install Python 3.12
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y \
        python3.12 \
        python3.12-venv \
        python3.12-dev && \
    rm -rf /var/lib/apt/lists/*

# Create a Python 3.12 virtual environment
RUN python3.12 -m venv /opt/venv

# Make Python 3.12 the default for subsequent Docker instructions
ENV PATH="/opt/venv/bin:$PATH"

# gcd files
# -- toggle GCD download at build time (1=download, 0=skip)
ARG INCLUDE_GCD=1
RUN set -eux; \
    mkdir -p /opt/i3-data/baseline_gcds; \
    if [ "${INCLUDE_GCD}" = "1" ]; then \
        wget -nv -N -t 5 -P /opt/i3-data/baseline_gcds -r -l 1 -A '*.i3*' -nd http://prod-exe.icecube.wisc.edu/baseline_gcds/; \
    else \
        echo "Skipping baseline_gcds download (INCLUDE_GCD=${INCLUDE_GCD})"; \
    fi; \
    chmod -R u+rwX,go+rX,go-w /opt/i3-data/baseline_gcds

#
# Setup source code / python packaging
#
ARG WORKDIR="/local"
WORKDIR $WORKDIR

# Mount the entire build context (including '.git/') just for this step
# NOTE:
#  - mounting '.git/' allows the Python project to build with 'setuptools-scm'
#  - no 'COPY' because we don't want to copy extra files (especially '.git/')
#  - using '/tmp/pip-cache' allows pip to cache
RUN --mount=type=cache,target=/tmp/pip-cache \
    pip install --upgrade "pip>=25" "setuptools>=80" "wheel>=0.45"

RUN --mount=type=bind,source=.,target=/src,rw \
    --mount=type=cache,target=/tmp/pip-cache \
    pip install "/src[rabbitmq]"

# optional diagnostics
RUN python --version
RUN pip freeze
RUN ls -la $WORKDIR

# physics config
ENV OPENBLAS_CORETYPE="Haswell"
ENV NPY_DISABLE_CPU_FEATURES="AVX512F,AVX512_KNL,AVX512_KNM,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512CD,AVX512_SKX"

# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/opt/icetray/bin/icetray-shell", "exec"]
CMD ["/bin/bash"]
