# FROM icecube/icetray:combo-V00-00-01-tensorflow.2.1.0-ubuntu18.04
# FROM icecube/icetray:combo-stable-tensorflow.1.13.2-ubuntu18.04
 FROM icecube/icetray:combo-stable-tensorflow2.4.1-ubuntu20.04
# optionally, try just `icecube/icetray:combo-stable-tensorflow`
# FROM icecube/icetray:combo-stable-tensorflow


#
# Get Data
#

# we need more spline tables (since we need to potentially re-do onlineL2)
RUN mkdir -p /opt/i3-data/photon-tables/splines/
RUN ls /opt/i3-data
RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_abs_z20a10_V2.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_abs_z20a10_V2.fits
RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_prob_z20a10_V2.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_prob_z20a10_V2.fits

# Make this tensorflow image "universal" (enable the library
# to load even in absence of libcuda.so linked in by nvidia-docker).
# This should make this work on both GPU and CPU systems.
RUN ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 && \
    echo "/usr/local/cuda/lib64/stubs" > /etc/ld.so.conf.d/z-cuda-stubs.conf && \
    ldconfig


#
# Setup Python
#

# from https://gist.github.com/jprjr/7667947#gistcomment-3684823

ENV PYTHON_VERSION 3.8.10

# Set of all dependencies needed for pyenv to work on Ubuntu
RUN apt-get update \
        && apt-get install -y --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget ca-certificates curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev mecab-ipadic-utf8 git

# Set-up necessary Env vars for PyEnv
ENV PYENV_ROOT /root/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# Install pyenv
RUN set -ex \
    && curl https://pyenv.run | bash \
    && pyenv update \
    && pyenv install $PYTHON_VERSION \
    && pyenv global $PYTHON_VERSION \
    && pyenv rehash

RUN python3 -V


#
# Add Python Packages
#

# add the pulsar client and some other python packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y bzip2 zstd && apt-get clean
RUN sudo apt-get install python3-pip -y
RUN pip3 install pulsar-client==2.6.0 && \
    pip3 install tqdm && \
    pip3 install backports.tempfile && \
    pip3 install psutil && \
    pip3 install pygcn && \
    pip3 install healpy


#
# Get IceTray Setup
#

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

# patch onlinel2filter.py (it tries to do some magic with the pulse masks
# which is unnecessary and makes assumptions that are not true for L2 data.)
COPY onlinel2filter.py.patch /local
RUN patch /usr/local/icetray/lib/icecube/filterscripts/onlinel2filter.py onlinel2filter.py.patch && \
    rm onlinel2filter.py.patch


#
# ENTRYPOINT
#

# set the entry point so that entrypoint.py is called by default with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh", "python3", "/local/entrypoint.py"]
CMD []
