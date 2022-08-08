"""Configuration constants"""

import dataclasses as dc
import os
from typing import Final

from wipac_dev_tools import from_environment_as_dataclass

# pylint:disable=invalid-name

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

# For commonly used keys
I3FRAME_NSIDE: Final = "SCAN_HealpixNSide"
I3FRAME_PIXEL: Final = "SCAN_HealpixPixel"
I3FRAME_POSVAR: Final = "SCAN_PositionVariationIndex"
I3FRAME_RECO_I3POSITION: Final = "PixelReco_position"
I3FRAME_RECO_TIME: Final = "PixelReco_time"
I3FRAME_RECO_LLH: Final = "PixelReco_llh"
I3FRAME_RECO_ENERGY: Final = "PixelReco_energy"


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing env vars, typed."""

    SKYSCAN_REPORT_INTERVAL_SEC: int = 5 * 60
    SKYSCAN_PLOT_INTERVAL_SEC: int = 30 * 60
    SKYSCAN_SLACK_API_KEY: str = ""
    SKYSCAN_SLACK_CHANNEL: str = "#gfu_live"

    def __post_init__(self) -> None:
        """Check values."""
        if self.SKYSCAN_REPORT_INTERVAL_SEC <= 0:
            raise ValueError(
                f"Env Var: SKYSCAN_REPORT_INTERVAL_SEC is not positive: {self.SKYSCAN_REPORT_INTERVAL_SEC}"
            )
        if self.SKYSCAN_PLOT_INTERVAL_SEC <= 0:
            raise ValueError(
                f"Env Var: SKYSCAN_PLOT_INTERVAL_SEC is not positive: {self.SKYSCAN_PLOT_INTERVAL_SEC}"
            )


env = from_environment_as_dataclass(EnvConfig)
