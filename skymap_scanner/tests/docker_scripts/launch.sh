#!/bin/sh

# From the README.md

set -x

# You can run the producer to send a scan like this.
# Notice that you are submitting the event with a specific name that you
# can use later in order to save all data:
# docker run --rm -i $1 producer $2 --broker pulsar://localhost:6650 --nside 1 -n test_event_01

# Then you can then start some workers to scan the jobs in the queue:
# docker run --rm -i $1 worker --broker pulsar://localhost:6650

# Finally, since there are 7 jobs per pixel (different reconstruction
# seeds in absolute position in the detector), they need to be collected
# for each pixel. You have to run one (or several) of these:
docker run --rm -i $1 collector --broker pulsar://localhost:6650

# Now, you can save the output queue into an .i3 file and have a look at
# it: (Note that saver will block until all frames have been processed.)
docker run --rm -v $PWD:/mnt -i $1 saver --broker pulsar://localhost:6650 --nside 16 -n test_event_01 -o /mnt/test_event_01.i3
docker run --rm -v $PWD:/mnt -i icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/test_event_01.i3
