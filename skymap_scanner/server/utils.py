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
            "Cannot Fetch Event: must provide either a filepath or a connection to SkyDriver"
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


def _is_pow_of_two(intval: int) -> bool:
    # I know, I know, no one likes bit shifting... buuuut...
    return isinstance(intval, int) and (intval > 0) and (intval & (intval - 1) == 0)


def validate_nside_progression(
    nside_progression: cfg.NSideProgression,
) -> cfg.NSideProgression:
    """Validate and sort the nside progression."""
    if len(set(n[0] for n in nside_progression)) != len(nside_progression):
        raise ValueError(
            f"Invalid NSide Progression: has duplicate nsides ({nside_progression})"
        )
    if [n[0] for n in nside_progression] != sorted(n[0] for n in nside_progression):
        raise ValueError(
            f"Invalid NSide Progression: nsides are not in ascending order ({nside_progression})"
        )
    if nside_progression[0][1] != cfg.FIRST_NSIDE_PIXEL_EXTENSION:
        raise ValueError(
            f"Invalid NSide Progression: the first pixel extension number must be {cfg.FIRST_NSIDE_PIXEL_EXTENSION} ({nside_progression})"
        )
    if any(not isinstance(n[1], int) or n[1] <= 0 for n in nside_progression[1:]):
        # don't check first extension #
        raise ValueError(
            f"Invalid NSide Progression: extension number must be positive int ({nside_progression})"
        )
    if any(not _is_pow_of_two(n[0]) for n in nside_progression):
        raise ValueError(
            f"Invalid NSide Progression: nside value must be positive n^2 ({nside_progression})"
        )
    return nside_progression
