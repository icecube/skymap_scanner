"""Configuration constants."""

import dataclasses as dc
import enum
from pathlib import Path
from typing import Final, List

from wipac_dev_tools import from_environment_as_dataclass

# pylint:disable=invalid-name

#
# True constants
#

DEFAULT_GCD_DIR: Path = Path("/opt/i3-data/baseline_gcds")

# Local data sources. These are assumed to be filesystem paths and are expected to have the same directory structure.
LOCAL_DATA_SOURCES: Final[List[Path]] = [
    Path("/opt/i3-data"),
    Path("/cvmfs/icecube.opensciencegrid.org/data"),
]
# Directory path under a local data source to fetch spline data from.
LOCAL_SPLINE_SUBDIR: Final[str] = "photon-tables/splines"

# HTTP source to download data from.
REMOTE_DATA_SOURCE: Final[str] = "http://prod-exe.icecube.wisc.edu"
REMOTE_SPLINE_SUBDIR: Final[str] = "spline-tables"

LOCAL_DATA_CACHE: Final[Path] = Path("./data-staging-cache")

# physics strings
INPUT_PULSES_NAME: Final = "SplitUncleanedInIcePulses"
INPUT_TIME_NAME: Final = "SeedVertexTime"
INPUT_POS_NAME: Final = "SeedVertexPos"
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

BASELINE_GCD_FILENAME = "base_GCD_for_diff.i3"
SOURCE_BASELINE_GCD_METADATA = "original_base_GCD_for_diff_filename.txt"
GCDQp_FILENAME = "GCDQp.i3"

PREDICTIVE_SCANNING_THRESHOLD_MIN = 0.1
PREDICTIVE_SCANNING_THRESHOLD_MAX = 1.0
PREDICTIVE_SCANNING_THRESHOLD_DEFAULT = 1.0

REPORTER_TIMELINE_PERCENTAGES = [
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.8,
    0.9,
    0.95,  # start narrowing to show outliers
    0.99,
    0.999,
    0.9999,
    0.99999,
    1.0,
]
COLLECTOR_BASE_THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


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
    SKYSCAN_BROKER_CLIENT: str = "rabbitmq"
    SKYSCAN_BROKER_ADDRESS: str = ""  # broker / mq address
    SKYSCAN_BROKER_AUTH: str = ""  # broker / mq auth token

    # TIMEOUTS
    #
    # seconds -- how long client waits between receiving pixels before thinking event scan is 100% done
    #  - set to `max(reco duration) + max(subsequent iteration startup time)`
    #  - think about starved clients
    #  - normal expiration scenario: the scan is done, no more pixels to scan (alternative: manually kill client process)
    SKYSCAN_MQ_TIMEOUT_TO_CLIENTS: int = 60 * 30  # 30 mins
    #
    # seconds -- how long server waits before thinking all clients are dead
    #  - set to duration of first reco + client launch (condor)
    #  - important if clients launch *AFTER* server
    #  - normal expiration scenario: all clients died (bad condor submit file), otherwise never (server knows when all recos are done)
    SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS: int = 3 * 24 * 60 * 60  # 3 days
    #
    # seconds -- how long client waits before first message (set to duration of server startup)
    #  - important if clients launch *BEFORE* server
    #  - normal expiration scenario: server died (ex: tried to read corrupted event file), otherwise never
    SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE: int = 60 * 60  # 60 mins

    EWMS_PILOT_TASK_TIMEOUT: int = 60 * 30

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
