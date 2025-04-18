"""Server-specific utils."""

import asyncio
import json
import logging
import math
import os
import pickle
import signal
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import mqclient as mq
from rest_tools.client import CalcRetryFromWaittimeMax, RestClient
from wipac_dev_tools.timing_tools import IntervalTimer

from . import SERVER_ENV
from ..recos import RecoInterface

LOGGER = logging.getLogger(__name__)


########################################################################################


def get_mqclient_connections() -> tuple[mq.Queue, mq.Queue]:
    """Establish connections to message queues."""
    with open(SERVER_ENV.SKYSCAN_EWMS_JSON) as f:
        ewms_config = json.load(f)

    to_clients_queue = mq.Queue(
        ewms_config["toclient"]["broker_type"],
        address=ewms_config["toclient"]["broker_address"],
        name=ewms_config["toclient"]["name"],
        auth_token=ewms_config["toclient"]["auth_token"],
        # timeout=-1,  # NOTE: this mq only sends messages so no timeout needed
    )

    from_clients_queue = mq.Queue(
        ewms_config["fromclient"]["broker_type"],
        address=ewms_config["fromclient"]["broker_address"],
        name=ewms_config["fromclient"]["name"],
        auth_token=ewms_config["fromclient"]["auth_token"],
        timeout=SERVER_ENV.SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS,
    )

    return to_clients_queue, from_clients_queue


########################################################################################


def connect_to_skydriver(urgent: bool) -> RestClient:
    """Get REST client for SkyDriver depending on the urgency."""
    if urgent:
        return RestClient(
            SERVER_ENV.SKYSCAN_SKYDRIVER_ADDRESS,
            token=SERVER_ENV.SKYSCAN_SKYDRIVER_AUTH,
            timeout=60.0,
            retries=CalcRetryFromWaittimeMax(waittime_max=1 * 60 * 60),
            # backoff_factor=0.3,
        )
    else:
        return RestClient(
            SERVER_ENV.SKYSCAN_SKYDRIVER_ADDRESS,
            token=SERVER_ENV.SKYSCAN_SKYDRIVER_AUTH,
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
    if not SERVER_ENV.SKYSCAN_SKYDRIVER_ADDRESS:
        return

    logger = logging.getLogger("skyscan.kill_switch")

    skydriver_rc = connect_to_skydriver(urgent=False)

    while True:
        await asyncio.sleep(SERVER_ENV.SKYSCAN_KILL_SWITCH_CHECK_INTERVAL)

        status = await skydriver_rc.request(
            "GET", f"/scan/{SERVER_ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/status"
        )

        if status["is_deleted"] or status["ewms_deactivated"]:
            logger.critical(
                f"Kill switch triggered by SkyDriver scan status: "
                f"{status['is_deleted']=} or {status['ewms_deactivated']=}"
            )
            os.kill(os.getpid(), signal.SIGINT)  # NOTE - sys.exit only exits thread


async def wait_for_workers_to_start() -> None:
    """Wait until SkyDriver indicates there are workers currently running."""
    if not SERVER_ENV.SKYSCAN_SKYDRIVER_ADDRESS:
        return

    skydriver_rc = connect_to_skydriver(urgent=False)
    timer = IntervalTimer(30, LOGGER)  # fyi: skydriver (feb '25) updates every 60s
    prev: dict[str, Any] = {}

    while True:  # yes, we are going to wait forever
        resp = await skydriver_rc.request(
            "GET", f"/scan/{SERVER_ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/ewms/workforce"
        )

        if resp != prev:
            LOGGER.info(f"workers: {resp}")  # why not log this, but just when updated
            prev = resp

        if resp["n_running"]:
            LOGGER.info("SkyDriver says there are workers running!")
            return
        else:
            LOGGER.info(
                f"SkyDriver says no workers are running (yet)"
                f"--checking again in {timer.seconds}s..."
            )
            await timer.wait_until_interval()


########################################################################################


async def fetch_event_contents_from_skydriver() -> Any:
    """Fetch event contents from SkyDriver."""
    skydriver_rc = connect_to_skydriver(urgent=True)

    manifest = await skydriver_rc.request(
        "GET", f"/scan/{SERVER_ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/manifest"
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


def calc_estimated_total_nside_recos(
    nside_progression: NSideProgression,
    reco: RecoInterface,
    n_posvar: int,
) -> Dict[int, int]:
    """Get # of recos per nside (w/ predictive scanning its a LOWER bound).

    The actual pixel generation is done iteratively, and does not
    rely on this function. Use this function for reporting & logging
    only.
    """

    def previous_nside(index: int) -> int:
        """Get previous nside value."""
        if index == 0:  # for the first nside use 1, since it's used to divide
            return 1
        return nside_progression.get_at_index(index - 1)[0]  # nside

    def get_nside_count(index: int, nside: int) -> int:
        """Get the estimated n recos for this nside."""
        if index == 0:
            if reco.pointing_dir_name is not None:
                # pointed scans do not use the full sky
                return (
                    math.ceil(  # N_approx ≈ 6 * nside ^ 2 * (1 - cos(R))
                        6 * nside**2 * (1 - math.cos(reco.ang_dist * (math.pi / 180)))
                    )
                    * n_posvar
                )
            else:
                factor = 12  # the base pixel count for HEALPix
        else:
            factor = nside_progression[nside]  # the pixel extension
        # get floor
        return int(n_posvar * factor * ((nside / previous_nside(index)) ** 2))

    # calculate each
    return {
        nside: get_nside_count(i, nside) for i, nside in enumerate(nside_progression)
    }
