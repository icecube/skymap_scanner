import os

GCD_base_dirs = [
os.path.join(os.environ("HOME"), "PoleBaseGCDs"), # why can't we reach anything from the followup nodes???
"file:///data/exp/IceCube/2016/internal-system/PoleBaseGCDs",
"http://icecube:skua@convey.icecube.wisc.edu/data/exp/IceCube/2016/internal-system/PoleBaseGCDs"]

slack_api_key = "---"
slack_channel = "#test_messaging"

del os
