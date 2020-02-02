# icetray:combo-stable-prod is the same as "slim",
# but also includes photon tables
# and baseline GCDs, both of which we need.
# FROM icecube/icetray:combo-stable-prod
FROM icecube/icetray:combo-stable-tensorflow.2.1.0-ubuntu18.04

# Make this tensorflow image "universal" (enable the library
# to load even in absence of libcuda.so linked in by nvidia-docker).
# This should make this work on both GPU and CPU systems.
RUN ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 && \
    echo "/usr/local/cuda/lib64/stubs" > /etc/ld.so.conf.d/z-cuda-stubs.conf && \
    ldconfig

# add the pulsar client and some other python packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python-pip bzip2 zstd && apt-get clean
RUN pip install pulsar-client==2.5.0 && \
    pip install tqdm && \
    pip install backports.tempfile

######### SNIP
##### TODO: remove this once icetray has been updated
# patch frame_object_diff here until we get a new release of icetray
COPY segments.py.patch /tmp/segments.py.patch
RUN patch /usr/local/icetray/lib/icecube/frame_object_diff/segments.py /tmp/segments.py.patch && rm /tmp/segments.py.patch
######### SNAP

# copy all .py files from the repository into the container image
COPY *.py /local/
WORKDIR /local

# add i3deepice to the container
COPY i3deepice/ /local/i3deepice/
ENV PYTHONPATH /local/i3deepice/

# set the entry point so that entrypoint.py is called by default with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh", "python", "/local/entrypoint.py"]
CMD []
