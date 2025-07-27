#
# Define the base image icetray version
#
ARG ICETRAY_VERSION=v1.15.3-ubuntu22.04

FROM icecube/icetray:icetray-devel-$ICETRAY_VERSION AS prod

# gcd files
RUN mkdir -p /opt/i3-data/baseline_gcds && \
    wget -nv -N -t 5 -P /opt/i3-data/baseline_gcds -r -l 1 -A *.i3* -nd http://prod-exe.icecube.wisc.edu/baseline_gcds/ && \
    chmod -R u+rwX,go+rX,go-w /opt/i3-data/baseline_gcds

#
# Setup source code / python packaging
#
ARG WORKDIR="/local"
WORKDIR $WORKDIR
COPY . .
RUN pip install .[rabbitmq]
# let's lee what's here...
RUN pip freeze
RUN ls -la $WORKDIR

# physics config
ENV OPENBLAS_CORETYPE="Haswell"
ENV NPY_DISABLE_CPU_FEATURES="AVX512F,AVX512_KNL,AVX512_KNM,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512CD,AVX512_SKX"
ENV I3PHOTOSPLINESERVICE_SHARE_MEMORY=1

# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/opt/icetray/bin/icetray-shell", "exec"]
CMD ["/bin/bash"]
