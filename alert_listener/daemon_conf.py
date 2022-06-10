# Set the rate of GFU prescaling. For GFU-only events, only 1 in N are sent out to slack.
gfu_prescale = 40.

# Hardcode path to GCD file on cvmfs
gcd_dir = "/cvmfs/icecube.opensciencegrid.org/users/RealTime/GCD/PoleBaseGCDs/"

# Configure slackids for user notifications
slackids = {'clagunas': 'UQ8LZG42G', 'mlincett': 'U01JSN2P32M'}

shifters_slackid = f"<@{slackids['mlincett']}>"
#shifters_slackid = f"<@{slackids['clagunas']}>, <@{slackids['mlincett']}>"
