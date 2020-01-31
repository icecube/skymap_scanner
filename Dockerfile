# icetray:combo-stable-prod is the same as "slim",
# but also includes photon tables
# and baseline GCDs, both of which we need.
FROM icecube/icetray:combo-stable-prod

# add the pulsar client
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python-pip bzip2 zstd && apt-get clean
RUN pip install pulsar-client==2.5.0 && \
    pip install tqdm && \
    pip install backports.tempfile

# copy in all .py files from the repository
COPY *.py /local/
WORKDIR /local

# set the entry point so that entrypoint.py is called by default with any parameters given to the `docker run` command
ENTRYPOINT ["/bin/bash", "/usr/local/icetray/env-shell.sh", "python", "/local/entrypoint.py"]
CMD []
