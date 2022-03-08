# ==============================================================================
# Set the rate of GFU prescaling.
# For GFU-only events, only 1 in N are sent out to slack
# ==============================================================================
gfu_prescale = 40.

# ==============================================================================
# Hardcode path to GCD file on cvmfs
# ==============================================================================
gcd_dir = "/cvmfs/icecube.opensciencegrid.org/users/RealTime/GCD/PoleBaseGCDs/"
#gcd_dir = os.path.join("/cvmfs/icecube.opensciencegrid.org/users/steinrob/GCD/PoleBaseGCDs/baseline_gcd_131577.i3")

# ==============================================================================
# Configure paths and ports for downloading/scanning
# ==============================================================================
distribute_numclients = 1000.
# distribute_port = "21339"

# ==============================================================================
# Configure slackids for user notifications
# Still a bit ugly but more readable than before.
# ==============================================================================
slackids = { 'clagunas': 'UQ8LZG42G', 'mlincett': 'U01JSN2P32M' }

shifters_slackid = f"<@{slackids['mlincett']}>" 
#shifters_slackid = f"<@{slackids['clagunas']}>, <@{slackids['mlincett']}>" 
