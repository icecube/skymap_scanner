"""Server-specific utils."""

import asyncio
import json
import logging
import os
import pickle
import signal
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cachetools.func
import mqclient as mq
from rest_tools.client import CalcRetryFromWaittimeMax, RestClient

from . import ENV

LOGGER = logging.getLogger(__name__)


########################################################################################


def get_mqclient_connections() -> tuple[mq.Queue, mq.Queue]:
    """Establish connections to message queues."""
    to_clients_queue = mq.Queue(
        ENV.SKYSCAN_MQ_TOCLIENT_BROKER_TYPE,
        address=ENV.SKYSCAN_MQ_TOCLIENT_BROKER_ADDRESS,
        name=ENV.SKYSCAN_MQ_TOCLIENT,
        auth_token=ENV.SKYSCAN_MQ_TOCLIENT_AUTH_TOKEN,
        # timeout=-1,  # NOTE: this mq only sends messages so no timeout needed
    )
    from_clients_queue = mq.Queue(
        ENV.SKYSCAN_MQ_FROMCLIENT_BROKER_TYPE,
        address=ENV.SKYSCAN_MQ_FROMCLIENT_BROKER_ADDRESS,
        name=ENV.SKYSCAN_MQ_FROMCLIENT,
        auth_token=ENV.SKYSCAN_MQ_FROMCLIENT_AUTH_TOKEN,
        timeout=ENV.SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS,
    )

    return to_clients_queue, from_clients_queue


########################################################################################


def connect_to_skydriver(urgent: bool) -> RestClient:
    """Get REST client for SkyDriver depending on the urgency."""
    if urgent:
        return RestClient(
            ENV.SKYSCAN_SKYDRIVER_ADDRESS,
            token=ENV.SKYSCAN_SKYDRIVER_AUTH,
            timeout=60.0,
            retries=CalcRetryFromWaittimeMax(waittime_max=1 * 60 * 60),
            # backoff_factor=0.3,
        )
    else:
        return RestClient(
            ENV.SKYSCAN_SKYDRIVER_ADDRESS,
            token=ENV.SKYSCAN_SKYDRIVER_AUTH,
            timeout=10.0,
            retries=1,
            # backoff_factor=0.3,
        )


async def nonurgent_request(rc: RestClient, args: dict[str, Any]) -> Any:
    """Request but if there's an error, don't raise it."""
    try:
        return await rc.request(**args)
    except Exception as e:
        LOGGER.warning(f"request to {rc.address} failed -- not fatal: {e}")
        return None


async def kill_switch_check_from_skydriver() -> None:
    """Routinely check SkyDriver whether to continue the scan."""
    if not ENV.SKYSCAN_SKYDRIVER_ADDRESS:
        return

    logger = logging.getLogger("skyscan.kill_switch")

    skydriver_rc = connect_to_skydriver(urgent=False)

    while True:
        await asyncio.sleep(ENV.SKYSCAN_KILL_SWITCH_CHECK_INTERVAL)

        status = await skydriver_rc.request(
            "GET", f"/scan/{ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/status"
        )

        if status["scan_state"].startswith("STOPPED__"):
            logger.critical(
                f"Kill switch triggered by SkyDriver scan state: {status['scan_state']}"
            )
            os.kill(os.getpid(), signal.SIGINT)  # NOTE - sys.exit only exits thread


########################################################################################


async def fetch_event_contents_from_skydriver() -> Any:
    """Fetch event contents from SkyDriver."""
    skydriver_rc = connect_to_skydriver(urgent=True)

    manifest = await skydriver_rc.request(
        "GET", f"/scan/{ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/manifest"
    )
    LOGGER.info("Fetched event contents from SkyDriver")
    return manifest["event_i3live_json_dict"]


def fetch_event_contents_from_file(event_file: Optional[Path]) -> dict:
    """Fetch event contents from file (.json or .pkl)."""
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


########################################################################################


def _is_pow_of_two(intval: int) -> bool:
    # I know, I know, no one likes bit shifting... buuuut...
    return isinstance(intval, int) and (intval > 0) and (intval & (intval - 1) == 0)


class NSideProgression(OrderedDict[int, int]):
    """Holds a valid progression of nsides & pixel-extension numbers."""

    # this is just a placeholder for the first iteration, which needs no
    # extension as all pixels over the sky are scanned
    FIRST_NSIDE_PIXEL_EXTENSION = 0
    DEFAULT = [(8, FIRST_NSIDE_PIXEL_EXTENSION), (64, 12), (512, 24)]

    HEALPIX_BASE_PIXEL_COUNT = 12

    def __init__(self, int_int_list: List[Tuple[int, int]]):
        super().__init__(NSideProgression._prevalidate(int_int_list))

    @property
    def min_nside(self) -> int:
        """Get the minimum (first) nside value."""
        return next(iter(self))

    def _get_int_int_list(self) -> List[Tuple[int, int]]:
        return list(self.items())

    @property
    def max_nside(self) -> int:
        """Get the minimum (first) nside value."""
        return next(reversed(self))

    def get_at_index(self, index: int) -> Tuple[int, int]:
        """Get nside value and pixel extension number at index."""
        return self._get_int_int_list()[index]

    def get_slice_plus_one(self, max_nside: Optional[int]) -> "NSideProgression":
        """Return a slice starting at the min nside + next nside if there.

        Provide `None` to return the first nside.

        Elements are shallow copies.
        """
        int_int_list = self._get_int_int_list()

        if max_nside is None:
            return NSideProgression([int_int_list[0]])

        if max_nside not in self.keys():
            raise ValueError(f"Cannot make slice (invalid nside): {max_nside}")

        if max_nside == self.max_nside:  # cannot do plus-one
            # (technically would work with python's slice syntax: [1,2][:10000] -> [1,2])
            return NSideProgression(int_int_list)

        index = list(self.keys()).index(max_nside)
        slice_plus_one = int_int_list[: index + 2]  # 8 & [8, 64, 512] -> [8, 64]
        return NSideProgression(slice_plus_one)

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
                f"Invalid NSide Progression: nside value must be positive 2^n ({int_int_list})"
            )
        return int_int_list

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(str(self._get_int_int_list()))

    @cachetools.func.lru_cache()
    def n_recos_by_nside_lowerbound(self, n_posvar: int) -> Dict[int, int]:
        """Get # of recos per nside (w/ predictive scanning its a LOWER bound).

        The actual pixel generation is done iteratively, and does not
        rely on this function. Use this function for reporting & logging
        only.
        """

        # override first pixel extension for the math (uses base pixel count)
        nside_factor_list = self._get_int_int_list()
        nside_factor_list[0] = (nside_factor_list[0][0], self.HEALPIX_BASE_PIXEL_COUNT)

        def previous_nside(index: int) -> int:
            # get previous nside value
            if index == 0:  # for the first nside use 1, since it's used to divide
                return 1
            return nside_factor_list[index - 1][0]  # nside

        return {
            nside: int(n_posvar * factor * ((nside / previous_nside(i)) ** 2))
            for i, (nside, factor) in enumerate(nside_factor_list)
        }
