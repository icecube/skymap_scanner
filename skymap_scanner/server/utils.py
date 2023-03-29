"""Server-specific utils."""


import json
import pickle
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cachetools.func
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


class NSideProgression(OrderedDict[int, int]):
    """Holds a valid progression of nsides."""

    FIRST_NSIDE_PIXEL_EXTENSION = 12  # this is mandated by HEALPix algorithm
    DEFAULT = [(8, FIRST_NSIDE_PIXEL_EXTENSION), (64, 12), (512, 24)]

    def __init__(self, int_int_list: List[Tuple[int, int]]):
        super().__init__(NSideProgression._prevalidate(int_int_list))

    @property
    def min_nside(self) -> int:
        """Get the minimum (first) nside value."""
        return next(iter(self))

    @staticmethod
    def _prevalidate(int_int_list: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Validate and sort the nside progression."""
        if len(set(n[0] for n in int_int_list)) != len(int_int_list):
            raise ValueError(
                f"Invalid NSide Progression: has duplicate nsides ({int_int_list})"
            )
        if [n[0] for n in int_int_list] != sorted(n[0] for n in int_int_list):
            raise ValueError(
                f"Invalid NSide Progression: nsides are not in ascending order ({int_int_list})"
            )
        if int_int_list[0][1] != NSideProgression.FIRST_NSIDE_PIXEL_EXTENSION:
            raise ValueError(
                f"Invalid NSide Progression: the first pixel extension number must be {NSideProgression.FIRST_NSIDE_PIXEL_EXTENSION} ({int_int_list})"
            )
        if any(not isinstance(n[1], int) or n[1] <= 0 for n in int_int_list[1:]):
            # don't check first extension #
            raise ValueError(
                f"Invalid NSide Progression: extension number must be positive int ({int_int_list})"
            )
        if any(not _is_pow_of_two(n[0]) for n in int_int_list):
            raise ValueError(
                f"Invalid NSide Progression: nside value must be positive n^2 ({int_int_list})"
            )
        return int_int_list

    @cachetools.func.lru_cache()
    def n_recos_by_nside_lowerbound(self, n_posvar: int) -> Dict[int, int]:
        """Get estimated # of recos per nside.

        These are ESTIMATES (w/ predictive scanning it's a LOWER bound).
        """
        nside_progression: List[Tuple[int, int]] = list(self.items())

        def previous_nside(n: Tuple[int, int]) -> int:
            # get previous nside value
            idx = nside_progression.index(n)
            if idx == 0:
                return 1
            return nside_progression[idx - 1][0]

        return {
            N[0]: int(n_posvar * N[1] * (N[0] / previous_nside(N)) ** 2)
            for N in nside_progression
        }

    @cachetools.func.lru_cache()
    def total_n_recos_lowerbound(self, n_posvar: int) -> int:
        """Get estimated # of total recos for the scan.

        These are ESTIMATES (w/ predictive scanning it's a LOWER bound).
        """
        return sum(self.n_recos_by_nside_lowerbound(n_posvar).values())
