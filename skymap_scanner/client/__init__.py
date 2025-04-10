"""The Skymap Scanner Client."""

import dataclasses as dc

from wipac_dev_tools import from_environment_as_dataclass

from .. import config as cfg


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing environment variables, typed."""

    # LOGGING VARS
    SKYSCAN_LOG: str = cfg.LOG_LEVEL_DEFAULT
    SKYSCAN_LOG_THIRD_PARTY: str = cfg.LOG_THIRD_PARTY_LEVEL_DEFAULT
    SKYSCAN_EWMS_PILOT_LOG: str = cfg.LOG_LEVEL_DEFAULT
    SKYSCAN_MQ_CLIENT_LOG: str = cfg.LOG_LEVEL_DEFAULT

    # TESTING/DEBUG VARS
    # NOTE - these are accessed via `os.getenv` -- ctrl+F for usages
    # _SKYSCAN_CI_MINI_TEST: bool = False  # run minimal variations for testing (mini-scale)
    # _SKYSCAN_CI_CRASH_DUMMY_PROBABILITY: float = 0.5  # for reco algo: crash-dummy


CLIENT_ENV = from_environment_as_dataclass(EnvConfig)
