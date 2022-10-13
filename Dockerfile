FROM icecube/icetray:combo-main-devel


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
RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_single_spice_bfr-v2_flat_z20_a5.abs.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_single_spice_bfr-v2_flat_z20_a5.abs.fits
RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_single_spice_bfr-v2_flat_z20_a5.prob.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_single_spice_bfr-v2_flat_z20_a5.prob.fits
RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_effectivedistance_spice_bfr-v2_z20.eff.fits \
        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_effectivedistance_spice_bfr-v2_z20.eff.fits

# install baseline GCDs
RUN mkdir /opt/i3-data/baseline_gcds && \
    wget -nv -N -t 5 -P /opt/i3-data/baseline_gcds -r -l 1 -A *.i3* -nd https://icecube:skua@convey.icecube.wisc.edu/data/user/followup/baseline_gcds/ && \
    chmod -R u+rwX,go+rX,go-w /opt/i3-data/baseline_gcds
RUN ls /opt/i3-data/baseline_gcds


#
# Setup Python
#

# from https://gist.github.com/jprjr/7667947#gistcomment-3684823

ENV PYTHON_VERSION 3.8.10

# Set of all dependencies needed for pyenv to work on Ubuntu
RUN apt-get install ca-certificates
RUN apt-get update
RUN apt-get install -y --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget ca-certificates curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev mecab-ipadic-utf8 git

# Set-up necessary Env vars for PyEnv
ENV PYENV_ROOT /root/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# Install pyenv
RUN set -ex \
    && curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash \
    && pyenv update \
    && pyenv install $PYTHON_VERSION \
    && pyenv global $PYTHON_VERSION \
    && pyenv rehash

RUN python3 -V


#
# Get IceTray Setup
#

# add realtime_gfu python checkout from V21-06-00
RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V21-06-00/realtime_gfu \
        /usr/local/icetray/realtime_gfu --username=icecube --password=skua --no-auth-cache && \
    ln -sf /usr/local/icetray/realtime_gfu/python /usr/local/icetray/lib/icecube/realtime_gfu
# add realtime_hese
RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V21-06-00/realtime_hese \
        /usr/local/icetray/realtime_hese --username=icecube --password=skua --no-auth-cache && \
    ln -sf /usr/local/icetray/realtime_hese/python /usr/local/icetray/lib/icecube/realtime_hese
# add realtime_tools
RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V21-06-00/realtime_tools \
        /usr/local/icetray/realtime_tools --username=icecube --password=skua --no-auth-cache && \
    ln -sf /usr/local/icetray/realtime_tools/python /usr/local/icetray/lib/icecube/realtime_tools


#
# Get directory tree organized
#

WORKDIR /local
COPY . .

RUN apt-get install tree
RUN tree -f /local
RUN tree -f $I3_TESTDATA
RUN tree -f $I3_DATA


#
# Add Python Packages
#

RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y bzip2 zstd && apt-get clean
RUN sudo apt-get install python3-pip -y
RUN python3 -m pip install --upgrade pip
RUN pip install .


#
# ENTRYPOINT
#

# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh"]
CMD []
