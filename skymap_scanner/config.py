"""Configuration constants."""

import dataclasses as dc
import logging
from pathlib import Path
from typing import Final, List

import mqclient
from wipac_dev_tools import from_environment_as_dataclass, logging_tools

# pylint:disable=invalid-name

#
# True constants
#


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
INPUT_PULSES_NAME_MAP: Final[dict[str, str]] = {
    "2021a": "SplitUncleanedInIcePulses",
    "2023a": "SplitInIcePulses",
}
DEFAULT_INPUT_PULSES_NAME: Final = "SplitUncleanedInIcePulses"

INPUT_PULSES_NAME = "SplitUncleanedInIcePulses"

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
STATEDICT_INPUT_PULSES: Final = "input_pulses_name"
#
MSG_KEY_RECO_ALGO: Final = "reco_algo"
MSG_KEY_PFRAME_PKL_B64: Final = "pframe_pkl_b64"
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

    #
    # REQUIRED
    #

    SKYSCAN_SKYDRIVER_SCAN_ID: str  # globally unique ID

    # to-client queue
    SKYSCAN_MQ_TOCLIENT: str
    SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN: str
    SKYSCAN_MQ_TOCLIENT_BROKER_TYPE: str
    SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS: str
    #
    # from-client queue
    SKYSCAN_MQ_FROMCLIENT: str
    SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN: str
    SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE: str
    SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS: str

    #
    # OPTIONAL
    #

    SKYSCAN_PROGRESS_INTERVAL_SEC: int = 1 * 60
    SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO: float = (
        # The size of the sample window (a percentage of the collected/finished recos)
        #   used to calculate the most recent runtime rate (sec/reco), then used to make
        #   predictions for overall runtimes: i.e. amount of time left.
        # Also, see SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN.
        0.1
    )
    SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN: int = (
        # NOTE: val should not be (too) below the num of workers (which is unknown, so make a good guess).
        #   In other words, if val is too low, then the rate is not representative of the
        #   worker-pool's concurrency; if val is too high, then the window is too large.
        # This is only useful for the first `val/SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO`
        #   num of recos, afterward the ratio is used.
        100
    )
    SKYSCAN_RESULT_INTERVAL_SEC: int = 2 * 60

    SKYSCAN_KILL_SWITCH_CHECK_INTERVAL: int = 5 * 60

    # TIMEOUTS
    #
    # seconds -- how long server waits before thinking all clients are dead
    #  - set to duration of first reco + client launch (condor)
    #  - important if clients launch *AFTER* server
    #  - normal expiration scenario: all clients died (bad condor submit file), otherwise never (server knows when all recos are done)
    SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS: int = 3 * 24 * 60 * 60  # 3 days

    # SKYDRIVER VARS
    SKYSCAN_SKYDRIVER_ADDRESS: str = ""  # SkyDriver REST interface address
    SKYSCAN_SKYDRIVER_AUTH: str = ""  # SkyDriver REST interface auth token

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
            mqclient.queue.LOGGER: ENV.SKYSCAN_MQ_CLIENT_LOG,  # type: ignore[dict-item]
        },
    )
