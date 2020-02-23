FROM icecube/icetray:combo-V00-00-01-tensorflow.2.1.0-ubuntu18.04

# we need more spline tables (since we need to potentially re-do onlineL2)
RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_abs_z20a10_V2.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_abs_z20a10_V2.fits && \
    wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_prob_z20a10_V2.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_prob_z20a10_V2.fits

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
    pip install backports.tempfile && \
    pip install psutil && \
    pip install pygcn

# add realtime_gfu python checkout from V19-11-00
RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V19-11-00/realtime_gfu \
        /usr/local/icetray/realtime_gfu --username=icecube --password=skua --no-auth-cache && \
    svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V19-11-00/realtime_hese \
        /usr/local/icetray/realtime_hese --username=icecube --password=skua --no-auth-cache && \
    svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V19-11-00/realtime_tools \
        /usr/local/icetray/realtime_tools --username=icecube --password=skua --no-auth-cache && \
    ln -sf /usr/local/icetray/realtime_gfu/python /usr/local/icetray/lib/icecube/realtime_gfu && \
    ln -sf /usr/local/icetray/realtime_hese/python /usr/local/icetray/lib/icecube/realtime_hese && \
    ln -sf /usr/local/icetray/realtime_tools/python /usr/local/icetray/lib/icecube/realtime_tools

# copy all .py files from the repository into the container image
COPY *.py /local/
WORKDIR /local

# add i3deepice to the container
COPY i3deepice/ /local/i3deepice/
ENV PYTHONPATH /local/i3deepice/

# set the entry point so that entrypoint.py is called by default with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh", "python", "/local/entrypoint.py"]
CMD []
