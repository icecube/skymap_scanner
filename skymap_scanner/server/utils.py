"""Server-specific utils."""


import json
import pickle
from pathlib import Path
from typing import Any, Optional

from rest_tools.client import RestClient

from .. import config as cfg
from . import LOGGER


def fetch_event_contents(
    event_file: Optional[Path], skydriver_rc: Optional[RestClient]
) -> Any:
    """Fetch event contents from file (.json or .pkl) or via SkyDriver."""
    # request from skydriver
    if skydriver_rc:
        manifest = skydriver_rc.request_seq(
            "GET", f"/scan/manifest/{cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID}"
        )
        LOGGER.info("Fetched event contents from SkyDriver")
        return manifest["event_i3live_json_dict"]

    if not event_file:
        raise RuntimeError(
            "Cannot Fetch Event: must provided either '--event-file FILEPATH' or '--skydriver ADDRESS'"
        )

    # json
    if event_file.suffix == ".json":
        with open(event_file, "r") as f:
            data = json.load(f)
    # pickle (presumed)
    else:
        with open(event_file, "rb") as f:
            data = pickle.load(f)

    LOGGER.info(f"Fetched event contents from file: {event_file}")
    return data
