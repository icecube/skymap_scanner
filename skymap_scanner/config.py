"""Configuration constants"""

import os
from typing import Final

from wipac_dev_tools import from_environment

GCD_BASE_DIRS: Final = [
    os.path.join(
        os.environ["HOME"], "PoleBaseGCDs"
    ),  # why can't we reach anything from the followup nodes???
    "file:///data/user/followup/baseline_gcds",
    "http://icecube:skua@convey.icecube.wisc.edu/data/user/followup/baseline_gcds",
    "file:///data/exp/IceCube/2016/internal-system/PoleBaseGCDs",
    "http://icecube:skua@convey.icecube.wisc.edu/data/exp/IceCube/2016/internal-system/PoleBaseGCDs",
    "file:///cvmfs/icecube.opensciencegrid.org/users/steinrob/GCD/PoleBaseGCDs/",
]

# Read ENV vars
ENV: Final = from_environment(
    {
        "SLACK_API_KEY": "",
        "SLACK_CHANNEL": "#gfu_live",
    }
)

# Set constants for easy access
SLACK_API_KEY: Final = ENV["SLACK_API_KEY"]
SLACK_CHANNEL: Final = ENV["SLACK_CHANNEL"]
