#!/bin/sh

MYDIR="$(dirname "$(readlink -f "$0")")"

# From the README.md

set -x

# You can run the producer to send a scan like this.
# Notice that you are submitting the event with a specific name that you
# can use later in order to save all data:
$MYDIR/launch_producer.sh $1

# Then you can then start some workers to scan the jobs in the queue:
$MYDIR/launch_worker.sh $1

# Finally, since there are 7 jobs per pixel (different reconstruction
# seeds in absolute position in the detector), they need to be collected
# # for each pixel. You have to run one (or several) of these:
$MYDIR/launch_collector.sh $1

# Now, you can save the output queue into an .i3 file and have a look at
# it: (Note that saver will block until all frames have been processed.)
$MYDIR/launch_saver.sh $1
docker run --rm -v $PWD:/mnt -i icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/test_event_01.i3
