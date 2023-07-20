#
# Define the base image icetray version
#
ARG ICETRAY_VERSION=v1.5.1-ubuntu22.04

FROM icecube/icetray:icetray-prod-$ICETRAY_VERSION as prod


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
# client-starter fails to install on architectures not supporting htcondor, so silently fail without the extra
RUN pip install .[client-starter,rabbitmq] || pip install .[rabbitmq]

RUN pip freeze


# set the entry point so that module is called with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh"]

CMD []
