"""The Skymap Scanner Central Server."""

import dataclasses as dc
from pathlib import Path

from wipac_dev_tools import from_environment_as_dataclass

from .. import config as cfg


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class ServerEnvConfig:
    """For storing environment variables, typed."""

    #
    # REQUIRED
    #

    SKYSCAN_SKYDRIVER_SCAN_ID: str  # globally unique ID
    SKYSCAN_EWMS_JSON: Path  # json file containing mq info

    #
    # OPTIONAL
    #

    SKYSCAN_PROGRESS_INTERVAL_SEC: int = 1 * 60
    SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO: float = (
        # The size of the sample window (a percentage of the collected/finished recos)
        #   used to calculate the most recent runtime rate (sec/reco), then used to make
        #   predictions for overall runtimes: i.e. amount of time left.
        # Also, see SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN.
        0.25
    )
    SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN: int = (
        # WARNING!
        #   THIS IS A MINIMUM!!! -- it's only useful for the first
        #   `val/SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO` num of recos;
        #   then, SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO is used.
        # NOTE: val should not be (too) below the num of workers (which is unknown, so make a good guess).
        #   In other words, if val is too low, then the rate is not representative of the
        #   worker-pool's concurrency; if val is TOO HIGH, then the window is TOO LARGE.
        400
    )
    SKYSCAN_RESULT_INTERVAL_SEC: int = 2 * 60

    SKYSCAN_KILL_SWITCH_CHECK_INTERVAL: int = 5 * 60

    SKYSCAN_MQ_PREFETCH_FROM_CLIENTS: int = (
        # What is prefetch?
        #   Maximum number of unacknowledged messages the consumer is allowed to have in-flight.
        #   With prefetch=1, mqclient waits for each ack before delivering the next message.
        #   Increasing this (e.g., 300) lets mqclient stream messages continuously without waiting.
        #   Going much higher (>300) typically gives only small additional throughput gains (diminishing returns).
        300
    )

    # TIMEOUTS
    #
    # seconds -- how long server waits before thinking *all* clients are dead
    #  - set to duration of longest reco + on-client startup time
    SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS: int = 2 * 60 * 60  # 2 hours

    # SKYDRIVER VARS
    SKYSCAN_SKYDRIVER_ADDRESS: str = ""  # SkyDriver REST interface address
    SKYSCAN_SKYDRIVER_AUTH: str = ""  # SkyDriver REST interface auth token

    # LOGGING VARS
    SKYSCAN_LOG: str = cfg.LOG_LEVEL_DEFAULT
    SKYSCAN_LOG_THIRD_PARTY: str = cfg.LOG_THIRD_PARTY_LEVEL_DEFAULT
    SKYSCAN_EWMS_PILOT_LOG: str = cfg.LOG_LEVEL_DEFAULT
    SKYSCAN_MQ_CLIENT_LOG: str = cfg.LOG_LEVEL_DEFAULT

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


SERVER_ENV = from_environment_as_dataclass(ServerEnvConfig)
