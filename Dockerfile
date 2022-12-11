#
# Define the base image icetray version
#
ARG ICETRAY_VERSION=v1.4.1-ubuntu22.04

FROM icecube/icetray:icetray-devel-$ICETRAY_VERSION as build

#
# Add Packages
#
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y zstd libzstd-dev protobuf-compiler python3-pybind11 python3-pip && \
    apt-get clean

#
# Manually compile Pulsar
#
WORKDIR /local
RUN git clone https://github.com/apache/pulsar-client-cpp
RUN cd pulsar-client-cpp && cmake -DBUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release . && make -j2 && make install
RUN git clone https://github.com/apache/pulsar-client-python
RUN cd pulsar-client-python && git submodule update --init \
    && cmake -B build \
    && cmake --build build && cmake --install build \
    && python3 ./setup.py bdist_wheel


#
# Now make the prod image
#
FROM icecube/icetray:icetray-prod-$ICETRAY_VERSION as prod


#
# Add Packages
#
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y libprotobuf23 python3-pybind11 python3-pip && \
    apt-get clean


#
# Copy pulsar
#
WORKDIR /local
COPY --from=build /usr/local/include/pulsar/ /usr/local/include/pulsar/
COPY --from=build /usr/local/lib/libpulsar* /usr/local/lib/
COPY --from=build /local/pulsar-client-python/dist/ pulsar-client-python/
RUN python3 -m pip install pulsar-client-python/pulsar_client-*.whl



# we need more spline tables (since we need to potentially re-do onlineL2)
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_abs_z20a10_V2.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_abs_z20a10_V2.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_prob_z20a10_V2.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_prob_z20a10_V2.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_single_spice_bfr-v2_flat_z20_a5.abs.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_single_spice_bfr-v2_flat_z20_a5.abs.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_single_spice_bfr-v2_flat_z20_a5.prob.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_single_spice_bfr-v2_flat_z20_a5.prob.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_effectivedistance_spice_bfr-v2_z20.eff.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_effectivedistance_spice_bfr-v2_z20.eff.fits


#
# Get IceTray Setup
#

# add realtime_gfu python checkout from V21-06-00
#RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V21-06-00/realtime_gfu \
#        /usr/local/icetray/realtime_gfu --username=icecube --password=skua --no-auth-cache && \
#    ln -sf /usr/local/icetray/realtime_gfu/python /usr/local/icetray/lib/icecube/realtime_gfu
# add realtime_hese
#RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V21-06-00/realtime_hese \
#        /usr/local/icetray/realtime_hese --username=icecube --password=skua --no-auth-cache && \
#    ln -sf /usr/local/icetray/realtime_hese/python /usr/local/icetray/lib/icecube/realtime_hese
# add realtime_tools
#RUN svn co http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V21-06-00/realtime_tools \
#        /usr/local/icetray/realtime_tools --username=icecube --password=skua --no-auth-cache && \
#    ln -sf /usr/local/icetray/realtime_tools/python /usr/local/icetray/lib/icecube/realtime_tools


#
# Add Python Packages
#
WORKDIR /local
COPY . .
RUN pip install .


# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh"]

CMD []
