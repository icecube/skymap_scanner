import os

GCD_base_dirs = [
os.path.join(os.environ["HOME"], "PoleBaseGCDs"), # why can't we reach anything from the followup nodes???
"file:///data/user/followup/baseline_gcds",
"http://icecube:skua@convey.icecube.wisc.edu/data/user/followup/baseline_gcds",
"file:///data/exp/IceCube/2016/internal-system/PoleBaseGCDs",
"http://icecube:skua@convey.icecube.wisc.edu/data/exp/IceCube/2016/internal-system/PoleBaseGCDs",
"file:///cvmfs/icecube.opensciencegrid.org/users/steinrob/GCD/PoleBaseGCDs/"]

slack_api_key = ""
# slack_channel = "#test_messaging"
slack_channel = "#gfu_live"
# slack_channel = "#amon-alerts"

del os
