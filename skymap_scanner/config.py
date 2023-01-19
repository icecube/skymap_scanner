"""Configuration constants."""

import dataclasses as dc
import enum
import os
from pathlib import Path
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

DEFAULT_GCD_DIR: Path = Path("/opt/i3-data/baseline_gcds")

MIN_NSIDE_DEFAULT: Final = 8
MAX_NSIDE_DEFAULT: Final = 512

# physics strings
INPUT_TIME_NAME: Final = "HESE_VHESelfVetoVertexTime"
INPUT_POS_NAME: Final = "HESE_VHESelfVetoVertexPos"
OUTPUT_PARTICLE_NAME: Final = "MillipedeSeedParticle"

# For commonly used keys
I3FRAME_NSIDE: Final = "SCAN_HealpixNSide"
I3FRAME_PIXEL: Final = "SCAN_HealpixPixel"
I3FRAME_POSVAR: Final = "SCAN_PositionVariationIndex"
#
STATEDICT_GCDQP_PACKET: Final = "GCDQp_packet"
STATEDICT_BASELINE_GCD_FILE: Final = "baseline_GCD_file"
STATEDICT_NSIDES: Final = "nsides"
#
MSG_KEY_RECO_ALGO: Final = "reco_algo"
MSG_KEY_PFRAME: Final = "pframe"


class RecoAlgo(enum.Enum):
    """The supported reconstruction algorithms."""

    MILLIPEDE_ORIGINAL = enum.auto()
    MILLIPEDE_WILKS = enum.auto()
    DUMMY = enum.auto()


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing environment variables, typed."""

    SKYSCAN_PROGRESS_INTERVAL_SEC: int = 1 * 60
    SKYSCAN_RESULT_INTERVAL_SEC: int = 2 * 60

    # BROKER/MQ VARS
    SKYSCAN_BROKER_ADDRESS: str = ""  # broker / mq address
    SKYSCAN_BROKER_AUTH: str = ""  # broker / mq auth token

    # TIMEOUTS
    #
    # seconds -- how long client waits between receiving pixels before thinking event scan is 100% done
    #  - set to `max(reco duration) + max(subsequent iteration startup time)`
    #  - think about starved clients
    #  - also determines final timeout (alternative: manually kill client process)
    SKYSCAN_MQ_TIMEOUT_TO_CLIENTS: int = 60 * 10
    #
    # seconds -- how long server waits before thinking all clients are dead
    #  - set to duration of first reco + cushion
    #  - important if CLIENTS LAUNCH *AFTER* SERVER
    SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS: int = 60 * (10 * 3)
    #
    # seconds -- how long client waits before first message (set to duration of server startup)
    #  - important if CLIENTS LAUNCH *BEFORE* SERVER
    SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE: int = 60 * 30

    # SKYDRIVER VARS
    SKYSCAN_SKYDRIVER_ADDRESS: str = ""  # SkyDriver REST interface address
    SKYSCAN_SKYDRIVER_AUTH: str = ""  # SkyDriver REST interface auth token
    SKYSCAN_SKYDRIVER_SCAN_ID: str = ""  # globally unique suffix for queue names

    # LOGGING VARS
    SKYSCAN_LOG: str = "INFO"
    SKYSCAN_LOG_THIRD_PARTY: str = "WARNING"

    # TESTING/DEBUG VARS
    SKYSCAN_MINI_TEST: bool = False  # run minimal variations for testing (mini-scale)

    def __post_init__(self) -> None:
        """Check values."""
        if self.SKYSCAN_PROGRESS_INTERVAL_SEC <= 0:
            raise ValueError(
                f"Env Var: SKYSCAN_PROGRESS_INTERVAL_SEC is not positive: {self.SKYSCAN_PROGRESS_INTERVAL_SEC}"
            )
        if self.SKYSCAN_RESULT_INTERVAL_SEC <= 0:
            raise ValueError(
                f"Env Var: SKYSCAN_RESULT_INTERVAL_SEC is not positive: {self.SKYSCAN_RESULT_INTERVAL_SEC}"
            )


ENV = from_environment_as_dataclass(EnvConfig)
