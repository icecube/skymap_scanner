# FROM icecube/ubuntu:2018.03.15-lightweight

##### first, install a base Ubuntu system (with development packages)

FROM ubuntu:16.04 as devel

MAINTAINER Claudio Kopper <ckopper@icecube.wisc.edu>

WORKDIR /root

# install system packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
  tar wget rsync gzip bzip2 xz-utils liblzma5 liblzma-dev zlib1g zlib1g-dev \
  less build-essential cmake libbz2-dev \
  libxml2-dev subversion libboost-python-dev \
  libboost-system-dev libboost-signals-dev libboost-thread-dev \
  libboost-date-time-dev libboost-serialization-dev \
  libboost-filesystem-dev libboost-program-options-dev \
  libboost-regex-dev libboost-iostreams-dev libgsl0-dev \
  libcdk5-dev libarchive-dev python-scipy \
  python-urwid python-numpy python-matplotlib \
  libz-dev libstarlink-pal-dev \
  libopenblas-dev libcfitsio3-dev libsprng2-dev \
  libsuitesparse-dev \
  libcfitsio3-dev libhdf5-serial-dev \
  python-numexpr cython python-cffi \
  python-healpy python-urllib3 python-jsonschema \
  python-requests \
  libzmq5 libzmq3-dev libzmqpp-dev libzmqpp3 python-zmq \
  python-dev python-pip nano vim sudo man-db lsb-release \
  && apt-get clean

# # allow passwordless sudo for users in the sudo group
# RUN echo "%sudo   ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/nopasswd_sudo
# 
# # create an icecube user
# RUN groupadd icecube && useradd -g icecube -d /home/icecube --create-home icecube && adduser icecube sudo
# RUN touch /home/icecube/.sudo_as_admin_successful
# USER icecube
# WORKDIR /home/icecube


######################## BASE SYSTEM DONE ########################
#### install icetray
##################################################################

# # switch back to root user
# USER root
# WORKDIR /root

# set up test data directory
RUN mkdir /opt/i3-data
ENV I3_DATA /opt/i3-data

# install I3_TESTDATA
RUN mkdir /opt/i3-data/i3-test-data
ENV I3_TESTDATA /opt/i3-data/i3-test-data

# # make sure to use the icecube user
# USER icecube
# WORKDIR /home/icecube

# check out icetray/combo/trunk
RUN mkdir /root/combo && mkdir /root/combo/build && \
    svn co http://code.icecube.wisc.edu/svn/meta-projects/combo/trunk \
           /root/combo/src --ignore-externals \
           --username=icecube --password=skua --no-auth-cache && \
    svn propget svn:externals /root/combo/src | grep \
      -e "^astro" \
      -e "^DomTools" \
      -e "^photospline" \
      -e "^lilliput" \
      -e "^photonics-service" \
      -e "^interfaces" \
      -e "^tableio" \
      -e "^serialization" \
      -e "^cmake" \
      -e "^icetray" \
      -e "^dataio" \
      -e "^dataclasses" \
      -e "^phys-services" \
      -e "^frame_object_diff" \
      -e "^VHESelfVeto" \
      -e "^full_event_followup" \
      -e "^gulliver" \
      -e "^millipede" \
      -e "^recclasses" \
      -e "^simclasses" \
      -e "^gulliver_modules" \
      -e "^photonics_service" \
      -e "^distribute" \
      | svn propset svn:externals /root/combo/src --file - && \
    svn update /root/combo/src \
        --username=icecube --password=skua --no-auth-cache && \
    svn co http://code.icecube.wisc.edu/svn/sandbox/ckopper/distribute \
           /root/combo/src/distribute \
           --username=icecube --password=skua --no-auth-cache

# # switch back to root user
# USER root
# WORKDIR /root

# install photon tables
RUN mkdir /opt/i3-data/photon-tables && \
    mkdir /opt/i3-data/photon-tables/splines && \
    wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/ems_mie_z20_a10.abs.fits       http://prod-exe.icecube.wisc.edu/spline-tables/ems_mie_z20_a10.abs.fits && \
    wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/ems_mie_z20_a10.prob.fits      http://prod-exe.icecube.wisc.edu/spline-tables/ems_mie_z20_a10.prob.fits

# # make sure to use the icecube user
# USER icecube
# WORKDIR /home/icecube

# install baseline GCDs
RUN mkdir /opt/i3-data/baseline_gcds && \
    wget -nv -N -t 5 -P /opt/i3-data/baseline_gcds -r -l 1 -A *.i3* -nd http://icecube:skua@convey.icecube.wisc.edu/data/user/followup/baseline_gcds/ && \
    chmod -R u+rwX,go+rX,go-w /opt/i3-data/baseline_gcds

# COPY --chown=icecube . /home/icecube/combo/src/skymap_scanner
# COPY --chown=root . /home/icecube/combo/src/skymap_scanner
COPY --chown=root CMakeLists.txt /root/combo/src/skymap_scanner/CMakeLists.txt
COPY --chown=root python /root/combo/src/skymap_scanner/python
RUN mkdir -p root/combo/src/skymap_scanner/resources/scripts

# build icetray
WORKDIR /root/combo/build
RUN cmake /root/combo/src \
      -DCMAKE_BUILD_TYPE=Release \
      -DINSTALL_TOOL_LIBS=OFF \
      -DUSE_GFILT=OFF \
      -DCMAKE_INSTALL_PREFIX=/usr/local/icetray \
    && make -j`nproc`

COPY --chown=root resources/scripts /root/combo/src/skymap_scanner/resources/scripts

# install icetray
RUN make install

# provide the entry point to run commands
ENTRYPOINT ["/bin/bash", "/root/combo/build/env-shell.sh", "exec"]
CMD ["/bin/bash"]

##################################################################
#### Now install a non-development system and move the
#### installation directory over from the previous build stage.
##################################################################

FROM ubuntu:16.04 as prod

MAINTAINER Claudio Kopper <ckopper@icecube.wisc.edu>

WORKDIR /root

# install system packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
  tar wget rsync gzip bzip2 xz-utils liblzma5 zlib1g \
  less \
  libboost-python1.58 \
  libboost-system1.58 libboost-signals1.58 libboost-thread1.58 \
  libboost-date-time1.58 libboost-serialization1.58 \
  libboost-filesystem1.58 libboost-program-options1.58 \
  libboost-regex1.58 libboost-iostreams1.58 libgsl2 \
  libcdk5 libarchive13 python-scipy \
  python-urwid python-numpy python-matplotlib \
  libz-dev libstarlink-pal0 \
  libopenblas-base libcfitsio2 libsprng2 \
  libsuitesparseconfig4.4.6 libspqr2.0.2 \
  libamd2.4.1 libcamd2.4.1 libbtf1.2.1 libcolamd2.9.1 \
  libccolamd2.9.1 libcholmod3.0.6 libcsparse3.1.4 libcxsparse3.1.4 \
  libklu1.3.3 libldl2.2.1 libumfpack5.7.1 \
  libcfitsio2 libhdf5-10 \
  python-numexpr cython python-cffi \
  python-healpy python-urllib3 python-jsonschema \
  python-requests \
  libzmq5 libzmqpp3 python-zmq \
  python lsb-release \
  && apt-get clean

# stage in icetray from the previous build
COPY --from=devel /usr/local/icetray /usr/local/icetray
COPY --from=devel /root/combo/src/skymap_scanner/resources/scripts/do_scan_for_json_blob.py /root/entrypoint.py
COPY --from=devel /opt/i3-data /opt/i3-data

# set environment variables
ENV I3_DATA /opt/i3-data
ENV I3_TESTDATA /opt/i3-data/i3-test-data
ENV TMPDIR /scratch

# build the matplotlib font cache (prevents warnings about the font cache on startup)
RUN python -c 'from matplotlib import pyplot'

# create the cache directory (there will probably be a volume mount here)
RUN mkdir -p /cache && mkdir -p /local && mkdir -p /scratch
VOLUME /cache

# we listen on port 12345 by default
EXPOSE 12345

# provide the entry point to run commands
WORKDIR /local
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh", "exec", "/root/entrypoint.py"]
CMD []
