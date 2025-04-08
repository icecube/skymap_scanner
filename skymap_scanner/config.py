"""Configuration constants."""

import dataclasses as dc
import logging
from pathlib import Path
from typing import Final, List
from collections import namedtuple

import ewms_pilot
import mqclient
from wipac_dev_tools import from_environment_as_dataclass, logging_tools

# pylint:disable=invalid-name

#
# True constants
#

EVENT_METADATA_VERSION: Final[int] = 1
DEFAULT_ANG_DIST: Final[float] = 3.5


# Local data sources. These are assumed to be filesystem paths and are expected to have the same directory structure.
LOCAL_DATA_SOURCES: Final[List[Path]] = [
    Path("/opt/i3-data"),
    Path("/cvmfs/icecube.opensciencegrid.org/data"),
]

# HTTP source to download data from.
REMOTE_DATA_SOURCE: Final[str] = "http://prod-exe.icecube.wisc.edu"

REMOTE_DATA_DOWNLOAD_RETRIES: Final[int] = 2  # note: attempts = retries + 1
REMOTE_DATA_DOWNLOAD_TIMEOUT: Final[int] = 15  # sec

# Local ephemeral directory to stage files.
LOCAL_DATA_CACHE: Final[Path] = Path("./data-staging-cache")

# Directory path under a local data source to fetch spline data from.
LOCAL_SPLINE_SUBDIR: Final[str] = "photon-tables/splines"
REMOTE_SPLINE_SUBDIR: Final[str] = "spline-tables"

# GCD data sources.
LOCAL_GCD_DATA_SOURCES: Final[List[Path]] = [
    Path("/opt/i3-data/baseline_gcds"),
    Path("/cvmfs/icecube.opensciencegrid.org/users/RealTime/GCD/PoleBaseGCDs"),
]

DEFAULT_GCD_DIR = LOCAL_GCD_DATA_SOURCES[0]

# Since the container and CVFMS have GCD files in different subdirectories
#   we put the complete path in LOCAL_GCD_DATA_SOURCES and use no subdir.
LOCAL_GCD_SUBDIR = ""

REMOTE_GCD_DATA_SOURCE: Final[str] = "http://prod-exe.icecube.wisc.edu/baseline_gcds"


# physics strings
KeyNames = namedtuple('KeyNames', 'pulseseries l2_splinempe')
# the keys for this dictionary correspond to the realtime "version" specified in event json
# in skymap_scanner the keys are referred to as the "realtime_format_version"
INPUT_KEY_NAMES_MAP: Final[dict[str, KeyNames]] = {
    "2021a": KeyNames("SplitUncleanedInIcePulses", "OnlineL2_SplineMPE"),
    "2023a": KeyNames("SplitInIcePulses", "l2_online_SplineMPE"),
    "2024a": KeyNames("SplitInIcePulses", "l2_online_SplineMPE"),
}
DEFAULT_INPUT_KEY_NAMES: Final = KeyNames("SplitUncleanedInIcePulses", "OnlineL2_SplineMPE")

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
MSG_KEY_PFRAME_PKL_B64: Final = "pframe_pkl_b64"
MSG_KEY_REALTIME_FORMAT_VERSION: Final = "realtime_format_version"
#
MSG_KEY_RECO_PIXEL_VARIATION_PKL_B64: Final = "reco_pixel_variation_pkl_b64"
MSG_KEY_RUNTIME: Final = "runtime"

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


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing environment variables, typed."""

    SKYSCAN_PROGRESS_INTERVAL_SEC: int = 1 * 60
    SKYSCAN_RESULT_INTERVAL_SEC: int = 2 * 60

    SKYSCAN_KILL_SWITCH_CHECK_INTERVAL: int = 5 * 60

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
    SKYSCAN_EWMS_PILOT_LOG: str = "INFO"
    SKYSCAN_MQ_CLIENT_LOG: str = "INFO"

    # TESTING/DEBUG VARS
    SKYSCAN_MINI_TEST: bool = False  # run minimal variations for testing (mini-scale)
    SKYSCAN_CRASH_DUMMY_PROBABILITY: float = 0.5  # for reco algo: crash-dummy

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


def configure_loggers() -> None:
    """Set up loggers with common configurations."""
    hand = logging.StreamHandler()
    hand.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)8s] %(name)s[%(process)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.getLogger().addHandler(hand)
    logging_tools.set_level(
        ENV.SKYSCAN_LOG,  # type: ignore[arg-type]
        first_party_loggers=__name__.split(".", maxsplit=1)[0],
        third_party_level=ENV.SKYSCAN_LOG_THIRD_PARTY,  # type: ignore[arg-type]
        future_third_parties=["google", "pika"],
        specialty_loggers={
            ewms_pilot.pilot.LOGGER: ENV.SKYSCAN_EWMS_PILOT_LOG,  # type: ignore[attr-defined, dict-item]
            mqclient.queue.LOGGER: ENV.SKYSCAN_MQ_CLIENT_LOG,  # type: ignore[dict-item]
        },
    )
