# syntax=docker/dockerfile:1.7

#
# Define the base image icetray version
#
ARG ICETRAY_VERSION=v1.15.3-ubuntu22.04

#FROM icecube/icetray:icetray-devel-$ICETRAY_VERSION AS prod
FROM icecube/icetray:icetray-devel-v1.15.3_pr4012-ubuntu22.04 AS prod

# gcd files
RUN mkdir -p /opt/i3-data/baseline_gcds && \
    wget -nv -N -t 5 -P /opt/i3-data/baseline_gcds -r -l 1 -A *.i3* -nd http://prod-exe.icecube.wisc.edu/baseline_gcds/ && \
    chmod -R u+rwX,go+rX,go-w /opt/i3-data/baseline_gcds

#
# Setup source code / python packaging
#
ARG WORKDIR="/local"
WORKDIR $WORKDIR

# Mount the entire build context (including .git) just for this step
# NOTE: no 'COPY' because we don't want to copy extra files (especially .git)
RUN --mount=type=bind,source=.,target=/src,rw \
    pip install --upgrade pip setuptools wheel \
 && pip install /src[rabbitmq]

# optional diagnostics
RUN pip freeze
RUN ls -la $WORKDIR

# physics config
ENV OPENBLAS_CORETYPE="Haswell"
ENV NPY_DISABLE_CPU_FEATURES="AVX512F,AVX512_KNL,AVX512_KNM,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512CD,AVX512_SKX"

# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/opt/icetray/bin/icetray-shell", "exec"]
CMD ["/bin/bash"]
