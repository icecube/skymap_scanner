"""Configuration constants."""

from pathlib import Path
from typing import Final, List
from collections import namedtuple

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

# default filepaths
BASELINE_GCD_FILENAME = "base_GCD_for_diff.i3"
SOURCE_BASELINE_GCD_METADATA = "original_base_GCD_for_diff_filename.txt"
GCDQp_FILENAME = "GCDQp.i3"

# predictive scanning config
PREDICTIVE_SCANNING_THRESHOLD_MIN = 0.1
PREDICTIVE_SCANNING_THRESHOLD_MAX = 1.0
PREDICTIVE_SCANNING_THRESHOLD_DEFAULT = 1.0
COLLECTOR_BASE_THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# reporter config
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


LOG_LEVEL_DEFAULT = "INFO"
LOG_THIRD_PARTY_LEVEL_DEFAULT = "WARNING"


#
# NOTE: Env var constants have been moved to server/__init__.py and client/__init__.py
#
