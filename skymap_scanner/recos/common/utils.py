from icecube.icetray import I3Frame
from datetime import datetime


def check_name(frame: I3Frame, logger, name: str) -> None:
    if name not in frame:
        raise RuntimeError(f"{name} not in frame.")
    else:
        logger.debug(f"Check that {name} is in frame: -> success.")


def notify_debug(frame: I3Frame, logger, message):
    logger.debug(f"{message} - {datetime.now()}")
