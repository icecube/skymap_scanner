#
# Define the base image icetray version
#
ARG ICETRAY_VERSION=v1.9.1-ubuntu22.04-X64

FROM icecube/icetray:icetray-prod-$ICETRAY_VERSION as prod

RUN mkdir -p /opt/i3-data/baseline_gcds && \
    wget -nv -N -t 5 -P /opt/i3-data/baseline_gcds -r -l 1 -A *.i3* -nd http://prod-exe.icecube.wisc.edu/baseline_gcds/ && \
    chmod -R u+rwX,go+rX,go-w /opt/i3-data/baseline_gcds

# we need more spline tables (since we need to potentially re-do onlineL2)
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_abs_z20a10_V2.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_abs_z20a10_V2.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/InfBareMu_mie_prob_z20a10_V2.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/InfBareMu_mie_prob_z20a10_V2.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_single_spice_ftp-v1_flat_z20_a5.abs.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_single_spice_ftp-v1_flat_z20_a5.abs.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_single_spice_ftp-v1_flat_z20_a5.prob.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_single_spice_ftp-v1_flat_z20_a5.prob.fits
#RUN wget -nv -t 5 -O /opt/i3-data/photon-tables/splines/cascade_effectivedistance_spice_ftp-v1_z20.eff.fits \
#        http://prod-exe.icecube.wisc.edu/spline-tables/cascade_effectivedistance_spice_ftp-v1_z20.eff.fits


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
RUN pip install .[rabbitmq]

RUN pip freeze

ENV OPENBLAS_CORETYPE="Haswell"
ENV NPY_DISABLE_CPU_FEATURES="AVX512F,AVX512_KNL,AVX512_KNM,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512CD,AVX512_SKX"

# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh"]

CMD []
