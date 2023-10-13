from icecube.icetray import I3Frame  # type: ignore[import]
from datetime import datetime


def check_name(frame: I3Frame, logger, key: str) -> None:
    if key not in frame:
        logger.debug(f"Check that {key} is in frame: -> FAIL.")
        raise RuntimeError(f"{key} not in frame.")
    else:
        logger.debug(f"Check that {key} is in frame: -> success.")


def notify_debug(frame: I3Frame, logger, message):
    logger.debug(f"{message} - {datetime.now()}")
