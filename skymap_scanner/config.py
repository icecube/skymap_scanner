"""Configuration constants"""

import os
from typing import Final, cast

from wipac_dev_tools import from_environment

#
# True constants
#

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

#
# Env var constants: set as constants for easy access
#

ENV: Final = from_environment(
    {
        "REPORT_INTERVAL_SEC": 5 * 60,
        "PLOT_INTERVAL_SEC": 30 * 60,
        "SLACK_API_KEY": "",
        "SLACK_CHANNEL": "#gfu_live",
    }
)

REPORT_INTERVAL_SEC: Final = cast(int, ENV["REPORT_INTERVAL_SEC"])
if REPORT_INTERVAL_SEC <= 0:
    raise ValueError(
        f"Env Var: REPORT_INTERVAL_SEC is not positive: {REPORT_INTERVAL_SEC}"
    )

PLOT_INTERVAL_SEC: Final = cast(int, ENV["PLOT_INTERVAL_SEC"])
if PLOT_INTERVAL_SEC <= 0:
    raise ValueError(f"Env Var: PLOT_INTERVAL_SEC is not positive: {PLOT_INTERVAL_SEC}")

SLACK_API_KEY: Final = ENV["SLACK_API_KEY"]
SLACK_CHANNEL: Final = ENV["SLACK_CHANNEL"]
