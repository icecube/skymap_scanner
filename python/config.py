import os

try:
    GCD_base_dirs = [os.path.join(os.environ["HOME"], "PoleBaseGCDs")] 
except KeyError: 
    GCD_base_dirs = [] # why can't we reach anything from the followup nodes???

GCD_base_dirs += ["file:///data/user/followup/baseline_gcds",
    "http://icecube:skua@convey.icecube.wisc.edu/data/user/followup/baseline_gcds",
    "file:///data/exp/IceCube/2016/internal-system/PoleBaseGCDs",
    "http://icecube:skua@convey.icecube.wisc.edu/data/exp/IceCube/2016/internal-system/PoleBaseGCDs"
]

slack_api_key = "---"
slack_channel = "#test_messaging"

del os
