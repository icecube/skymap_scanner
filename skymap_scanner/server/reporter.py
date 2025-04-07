"""Contains a class for reporting progress and result for a scan."""

import bisect
import dataclasses as dc
import datetime as dt
import itertools
import json
import logging
import math
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from rest_tools.client import RestClient
from skyreader import EventMetadata, SkyScanResult

from . import ENV
from .utils import NSideProgression, connect_to_skydriver, nonurgent_request
from .. import config as cfg
from ..utils import to_skyscan_result
from ..utils.pixel_classes import NSidesDict
from ..utils.utils import pyobj_to_string_repr

LOGGER = logging.getLogger(__name__)

StrDict = Dict[str, Any]


class WorkerStats:
    """Holds stats for the per-reco/worker level.

    "Worker runtime"  - the time actually spent doing a reco
    "Round-trip time" - the time a pixel takes from server, to worker,
                        and back -- includes any time spent on worker(s)
                        that died mid-reco
    """

    def __init__(
        self,
        on_worker_runtimes: list[float],
        on_server_roundtrips: list[float],
        on_server_roundtrip_starts: list[float],
        on_server_roundtrip_ends: list[float],
        initial_count: int = 0,
    ) -> None:

        #
        # PRIVATE
        # note -- these are private so the lists can be sampled to reduce memory
        #

        self._on_worker_runtimes = on_worker_runtimes
        self._on_worker_runtimes.sort()  # speed up stats
        #
        self._on_server_roundtrips = on_server_roundtrips
        self._on_server_roundtrips.sort()  # speed up stats
        #
        self._on_server_roundtrip_starts: List[float] = on_server_roundtrip_starts
        self._on_server_roundtrip_starts.sort()  # speed up stats
        #
        self._on_server_roundtrip_ends = on_server_roundtrip_ends
        self._on_server_roundtrip_ends.sort()  # speed up stats

        #
        # PUBLIC
        #

        self.count = initial_count

        # statistics functions...

        self.on_server_first_roundtrip_start = lambda: min(
            self._on_server_roundtrip_starts
        )
        self.on_server_last_roundtrip_end = lambda: max(self._on_server_roundtrip_ends)

        self.fastest_worker = lambda: min(self._on_worker_runtimes)
        self.fastest_roundtrip = lambda: min(self._on_server_roundtrips)

        self.slowest_worker = lambda: max(self._on_worker_runtimes)
        self.slowest_roundtrip = lambda: max(self._on_server_roundtrips)

        # Fast, floating point arithmetic mean.
        self.mean_worker = lambda: statistics.fmean(self._on_worker_runtimes)
        self.mean_roundtrip = lambda: statistics.fmean(self._on_server_roundtrips)

        # Median (middle value) of data.
        self.median_worker = lambda: float(statistics.median(self._on_worker_runtimes))
        self.median_roundtrip = lambda: float(
            statistics.median(self._on_server_roundtrips)
        )

        # other statistics functions...
        # geometric_mean Geometric mean of data.
        # harmonic_mean Harmonic mean of data.
        # median_low  # Low median of data.
        # median_high  # High median of data.
        # median_grouped  # Median, or 50th percentile, of grouped data.
        # mode  # Mode (most common value) of data.
        # pvariance  # Population variance of data.
        # variance  # Sample variance of data.
        # pstdev  # Population standard deviation of data.
        # stdev  # Sample standard deviation of data.

    def update(
        self,
        on_worker_runtime: float,
        on_server_roundtrip_start: float,
        on_server_roundtrip_end: float,
        increment_count: int,
    ) -> "WorkerStats":
        """Insert the runtime and recalculate round-trip start/end times."""
        self.count += increment_count

        # FUTURE DEV: sample these instead, i.e. flip a coin, heads:update, tails:noop

        # these must be sorted in order for the statistics functions to be quick
        bisect.insort(
            self._on_worker_runtimes,
            on_worker_runtime,
        )
        bisect.insort(
            self._on_server_roundtrips,
            on_server_roundtrip_end - on_server_roundtrip_start,
        )
        bisect.insort(
            self._on_server_roundtrip_starts,
            on_server_roundtrip_start,
        )
        bisect.insort(
            self._on_server_roundtrip_ends,
            on_server_roundtrip_end,
        )
        return self

    def get_summary(self) -> Dict[str, Dict[str, str]]:
        """Make a human-readable dict summary of the instance."""
        return {
            "worker time": {
                # worker times
                "mean": str(
                    dt.timedelta(seconds=int(self.mean_worker()))  # type: ignore[no-untyped-call]
                ),
                "median": str(
                    dt.timedelta(seconds=int(self.median_worker()))  # type: ignore[no-untyped-call]
                ),
                "slowest": str(
                    dt.timedelta(seconds=int(self.slowest_worker()))  # type: ignore[no-untyped-call]
                ),
                "fastest": str(
                    dt.timedelta(seconds=int(self.fastest_worker()))  # type: ignore[no-untyped-call]
                ),
            },
            "round-trip time": {
                "mean": str(
                    dt.timedelta(seconds=int(self.mean_roundtrip()))  # type: ignore[no-untyped-call]
                ),
                "median": str(
                    dt.timedelta(seconds=int(self.median_roundtrip()))  # type: ignore[no-untyped-call]
                ),
                "slowest": str(
                    dt.timedelta(seconds=int(self.slowest_roundtrip()))  # type: ignore[no-untyped-call]
                ),
                "fastest": str(
                    dt.timedelta(seconds=int(self.fastest_roundtrip()))  # type: ignore[no-untyped-call]
                ),
            },
            "wall time": {
                "start": str(
                    dt.datetime.fromtimestamp(
                        int(self.on_server_first_roundtrip_start())
                    )
                ),
                "end": str(
                    dt.datetime.fromtimestamp(int(self.on_server_last_roundtrip_end()))
                ),
                "runtime": str(
                    dt.timedelta(
                        seconds=int(
                            self.on_server_last_roundtrip_end()
                            - self.on_server_first_roundtrip_start()
                        )
                    )
                ),
                "mean reco": str(
                    dt.timedelta(
                        seconds=int(
                            (
                                self.on_server_last_roundtrip_end()
                                - self.on_server_first_roundtrip_start()
                            )
                            / self.count
                        )
                    )
                ),
            },
        }


class WorkerStatsCollection:
    """A performant collection of WorkerStats instances."""

    def __init__(self) -> None:
        self._worker_stats_by_nside: Dict[int, WorkerStats] = {}
        self._aggregate: Optional[WorkerStats] = None

    def get_runtime_prediction_technique(self) -> str:
        """Get a human-readable string of what technique is used for predicting runtimes."""
        if (
            self.runtime_sample_window_size
            == ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN
        ):
            return (
                f"simple average over entire scan runtime "
                f"(a moving average with a window of "
                f"{ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO} "
                f"will be used after "
                f"{int(ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN/ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO)} "
                f"recos have finished)"
            )
        else:
            return f"simple moving average (window={self.runtime_sample_window_size})"

    @property
    def _runtime_sample_window_size_candidate(self) -> int:
        """The window size that would be used if not for a minimum."""
        return int(self.total_ct * ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO)

    @property
    def runtime_sample_window_size(self) -> int:
        """The size of the window used for predicting runtimes."""
        return max(
            self._runtime_sample_window_size_candidate,
            ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_MIN,
        )

    def on_server_recent_sec_per_reco_rate(self) -> float:
        """The sec/reco rate from server pov within a moving window."""
        try:
            # look at a window, so don't use the first start time
            #   psst, we know that this list is sorted, ascending
            nth_most_recent_start = self.aggregate._on_server_roundtrip_starts[
                -self.runtime_sample_window_size
            ]
            n_recos = self.runtime_sample_window_size
        except IndexError:
            # not enough recos to sample, so take all of them
            nth_most_recent_start = self.aggregate.on_server_first_roundtrip_start()
            n_recos = self.total_ct

        return (
            self.aggregate.on_server_last_roundtrip_end() - nth_most_recent_start
        ) / n_recos

    def ct_by_nside(self, nside: int) -> int:
        """Get length per given nside."""
        try:
            return self._worker_stats_by_nside[nside].count
        except KeyError:
            return 0

    @property
    def total_ct(self) -> int:
        """Get the total count of all work units (recos)."""
        return sum(w.count for w in self._worker_stats_by_nside.values())

    @property
    def first_roundtrip_start(self) -> float:
        """Get the first roundtrip start time from server pov."""
        return self.aggregate.on_server_first_roundtrip_start()

    def update(
        self,
        nside: int,
        on_worker_runtime: float,
        on_server_roundtrip_start: float,
        on_server_roundtrip_end: float,
    ) -> int:
        """Return reco-count of nside's list after updating."""
        self._aggregate = None  # clear
        try:
            worker_stats = self._worker_stats_by_nside[nside]
            worker_stats.update(
                on_worker_runtime,
                on_server_roundtrip_start,
                on_server_roundtrip_end,
                increment_count=1,
            )
        except KeyError:
            worker_stats = self._worker_stats_by_nside[nside] = WorkerStats(
                on_worker_runtimes=[on_worker_runtime],
                on_server_roundtrips=[
                    on_server_roundtrip_end - on_server_roundtrip_start
                ],
                on_server_roundtrip_starts=[on_server_roundtrip_start],
                on_server_roundtrip_ends=[on_server_roundtrip_end],
                initial_count=1,
            )
        return worker_stats.count

    @property
    def aggregate(self) -> WorkerStats:
        """An aggregate (`WorkerStats` obj) of all recos (all nsides)."""
        if not self._aggregate:
            instances = self._worker_stats_by_nside.values()
            if not instances:
                return WorkerStats([], [], [], [])
            self._aggregate = WorkerStats(
                on_worker_runtimes=list(
                    itertools.chain(*[i._on_worker_runtimes for i in instances])
                ),
                on_server_roundtrips=list(
                    itertools.chain(*[i._on_server_roundtrips for i in instances])
                ),
                on_server_roundtrip_starts=list(
                    itertools.chain(*[i._on_server_roundtrip_starts for i in instances])
                ),
                on_server_roundtrip_ends=list(
                    itertools.chain(*[i._on_server_roundtrip_ends for i in instances])
                ),
                initial_count=self.total_ct,
            )
        return self._aggregate

    def get_summary(self) -> StrDict:
        """Make human-readable dict summaries for all nsides & an aggregate."""
        dicto: StrDict = {"all recos": self.aggregate.get_summary()}
        for nside, worker_stats in self._worker_stats_by_nside.items():
            dicto[f"nside-{nside}"] = worker_stats.get_summary()
        return dicto


class Reporter:
    """Manage means for reporting progress & results during/after the scan."""

    def __init__(
        self,
        global_start_time: float,
        nsides_dict: NSidesDict,
        n_posvar: int,
        nside_progression: NSideProgression,
        estimated_total_nside_recos: dict[int, int],
        output_dir: Optional[Path],
        event_metadata: EventMetadata,
        predictive_scanning_threshold: float,
    ) -> None:
        """
        Arguments:
            `global_start_time`
                - the start time (epoch) of the entire scan
            `nsides_dict`
                - the nsides_dict
            `n_posvar`
                - number of position variations per pixel
            `nside_progression`
                - the list of nsides & pixel-extensions
            `estimated_total_nside_recos`
                - the **estimated** total number of recos keyed by nside
            `output_dir`
                - a directory to write out results & progress
            `event_metadata`
                - a collection of metadata about the event
            `predictive_scanning_threshold`
                - the predictive scanning threshold (used only for reporting)

        Environment Variables:
            `SKYSCAN_PROGRESS_INTERVAL_SEC`
                - produce a progress report with this interval
            `SKYSCAN_RESULT_INTERVAL_SEC`
                - produce a (partial) skymap result with this interval
        """
        self.is_event_scan_done = False
        self.predictive_scanning_threshold = predictive_scanning_threshold

        self.global_start = global_start_time
        self.nsides_dict = nsides_dict

        if n_posvar <= 0:
            raise ValueError(f"n_posvar is not positive: {n_posvar}")
        self.n_posvar = n_posvar
        self.nside_progression = nside_progression
        self.estimated_total_nside_recos = estimated_total_nside_recos

        self._n_sent_by_nside: Dict[int, int] = {}

        if not ENV.SKYSCAN_SKYDRIVER_ADDRESS:
            self.skydriver_rc_nonurgent: Optional[RestClient] = None
            self.skydriver_rc_urgent: Optional[RestClient] = None
        else:
            self.skydriver_rc_nonurgent = connect_to_skydriver(urgent=False)
            self.skydriver_rc_urgent = connect_to_skydriver(urgent=True)

        self.output_dir = output_dir
        self.event_metadata = event_metadata

        # all set by calling initial_report()
        self.last_time_reported = 0.0
        self.last_time_reported_skymap = 0.0
        self.time_of_first_reco_start_on_client = 0.0
        self.worker_stats_collection: WorkerStatsCollection = WorkerStatsCollection()

        self._call_order = {
            "current_previous": {  # current_fucntion: previous_fucntion
                self.precomputing_report: [None],
                self.record_reco: [self.precomputing_report, self.record_reco],
                self.after_computing_report: [self.record_reco],
            },
            "last_called": None,
        }

    def _check_call_order(self, current: Callable) -> None:  # type: ignore[type-arg]
        """Make sure we're calling everything in order."""
        if (
            self._call_order["last_called"]  # type: ignore[operator]
            not in self._call_order["current_previous"][current]  # type: ignore[index]
        ):
            RuntimeError(f"Out of order execution: {self._call_order['last_called']=}")
        self._call_order["last_called"] = current  # type: ignore[assignment]

    def increment_sent_ct(self, nside: int) -> None:
        """Increment the number sent by nside."""
        try:
            self._n_sent_by_nside[nside] += 1
        except KeyError:
            self._n_sent_by_nside[nside] = 1

    async def precomputing_report(self) -> None:
        """Make a report before ANYTHING is computed."""
        self._check_call_order(self.precomputing_report)
        await self._send_progress(summary_msg="The Skymap Scanner has started up.")

    async def record_reco(
        self,
        nside: int,
        on_worker_runtime: float,
        on_server_roundtrip_start: float,
        on_server_roundtrip_end: float,
    ) -> None:
        """Send reports/logs/plots if needed."""
        self._check_call_order(self.record_reco)

        if not self.time_of_first_reco_start_on_client:
            # timeline: on_server_roundtrip_start -> pre-reco queue time -> (runtime) -> post-reco queue time -> on_server_roundtrip_end
            # since worker nodes need to startup & a pixel may fail several times before being reco'd,
            # we know "pre-reco queue time" >>> "post-reco queue time"
            # if we assume "post-reco queue time" ~= 0.0, then the reco started here:
            self.time_of_first_reco_start_on_client = on_server_roundtrip_end - (
                on_worker_runtime + 0.0
            )

        # update stats
        nside_ct = self.worker_stats_collection.update(
            nside,
            on_worker_runtime,
            on_server_roundtrip_start,
            on_server_roundtrip_end,
        )

        # make report(s)
        if nside_ct == 1:
            # always report the first received so we know things are rolling
            await self.make_reports_if_needed(bypass_timers=True)
        else:
            await self.make_reports_if_needed()

    async def make_reports_if_needed(
        self,
        bypass_timers: bool = False,
        summary_msg: str = "The Skymap Scanner is busy scanning pixels.",
    ) -> None:
        """Send reports/logs/plots if needed."""
        LOGGER.info(f"Collected: {self.worker_stats_collection.total_ct}")

        # check if we need to send a report to the logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported > ENV.SKYSCAN_PROGRESS_INTERVAL_SEC
        ):
            self.last_time_reported = current_time
            if self.worker_stats_collection.total_ct == 0:
                epilogue_msg = "I will report back when I start getting recos."
            else:
                epilogue_msg = (
                    f"I will report back again in "
                    f"{ENV.SKYSCAN_PROGRESS_INTERVAL_SEC} seconds if I have an update."
                )
            await self._send_progress(summary_msg, epilogue_msg)

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported_skymap
            > ENV.SKYSCAN_RESULT_INTERVAL_SEC
        ):
            self.last_time_reported_skymap = current_time
            await self._send_result()

    def _get_result(self) -> SkyScanResult:
        """Get SkyScanResult."""
        return to_skyscan_result.from_nsides_dict(
            self.nsides_dict,
            self.is_event_scan_done,
            self.event_metadata,
        )

    def predicted_total_recos(self) -> int:
        """Get a prediction for total number of recos for the entire scan.

        If the scan is done, use the # of recos sent.
        """
        if self.is_event_scan_done:
            return sum(self._n_sent_by_nside[nside] for nside in self.nside_progression)

        estimates_with_sents = sum(
            self._n_sent_by_nside.get(nside, self.estimated_total_nside_recos[nside])
            for nside in self.nside_progression
        )
        # estimates-sum SHOULD be a lower bound, but if estimates_with_sents
        #   is less than there will be more recos sent in the future
        return max(estimates_with_sents, sum(self.estimated_total_nside_recos.values()))

    def _get_processing_progress(self) -> StrDict:
        """Get a multi-line report on processing stats."""
        proc_stats: StrDict = {
            "start": {
                "scanner start": str(dt.datetime.fromtimestamp(int(self.global_start)))
            },
            "runtime": {
                "elapsed": str(
                    dt.timedelta(seconds=int(time.time() - self.global_start))
                ),
            },
        }

        if not self.worker_stats_collection.total_ct:  # still waiting
            return proc_stats

        # stats now that we have reco(s)
        elapsed_reco_server_walltime = (
            time.time() - self.worker_stats_collection.first_roundtrip_start
        )
        startup_runtime = (
            self.worker_stats_collection.first_roundtrip_start - self.global_start
        )
        proc_stats["start"].update(
            {
                "reco start (on server)": str(
                    dt.datetime.fromtimestamp(
                        int(self.worker_stats_collection.first_roundtrip_start)
                    )
                ),
                "reco start (on first worker)": str(
                    dt.datetime.fromtimestamp(
                        int(self.time_of_first_reco_start_on_client)
                    )
                ),
            }
        )
        proc_stats["runtime"].update(
            {
                "startup runtime": str(dt.timedelta(seconds=int(startup_runtime))),
                "reco runtime (on server)": str(
                    dt.timedelta(seconds=int(elapsed_reco_server_walltime))
                ),
                "reco start delay (on first worker)": str(
                    dt.timedelta(
                        seconds=int(
                            self.time_of_first_reco_start_on_client
                            - self.worker_stats_collection.first_roundtrip_start
                        )
                    )
                ),
            }
        )

        # add rates
        proc_stats["rate"] = self.worker_stats_collection.get_summary()

        # end stats OR predictions
        if self.is_event_scan_done:
            # SCAN IS DONE
            proc_stats["end"] = str(dt.datetime.fromtimestamp(int(time.time())))
            proc_stats["finished"] = True
        else:
            # MAKE PREDICTIONS
            n_recos_left = (
                self.predicted_total_recos() - self.worker_stats_collection.total_ct
            )
            time_left = (  # this uses a moving window average
                self.worker_stats_collection.on_server_recent_sec_per_reco_rate()
                * n_recos_left  # (sec/recos) * (recos/1) -> sec
            )
            proc_stats["predictions"] = {
                "time left": str(dt.timedelta(seconds=int(time_left))),
                "total runtime at finish": str(
                    dt.timedelta(
                        seconds=int(
                            startup_runtime + elapsed_reco_server_walltime + time_left
                        )
                    )
                ),
                "total # of reconstructions": self.predicted_total_recos(),
                "end": str(dt.datetime.fromtimestamp(int(time.time() + time_left))),
                "technique": self.worker_stats_collection.get_runtime_prediction_technique(),
            }

        return proc_stats

    def _get_tallies(self) -> StrDict:
        """Get a multi-dict progress report of the nsides_dict's contents."""

        def pixels_done(nside: int) -> int:
            return len(self.nsides_dict.get(nside, []))

        def n_sent_recos(nside: int) -> float:
            return self._n_sent_by_nside[nside] / self.n_posvar

        tallies_by_nside = {}
        # get done counts & percentages (estimates for future nsides)
        for nside in self.nside_progression:  # sorted by nside
            tallies_by_nside[nside] = {
                "recos": {
                    "done": self.worker_stats_collection.ct_by_nside(nside),
                    "done est. percent": (
                        (  # ex: 1/7 (0.1429)
                            f"{self.worker_stats_collection.ct_by_nside(nside)}/{self._n_sent_by_nside[nside]} "
                            f"({self.worker_stats_collection.ct_by_nside(nside) / self._n_sent_by_nside[nside]:.4f})"
                        )
                        if nside in self._n_sent_by_nside
                        else "N/A"
                    ),
                    "generated total": self._n_sent_by_nside[nside],
                    "initial approx. total": self.estimated_total_nside_recos[nside],
                },
                "pixels": {
                    "done": pixels_done(nside),
                    "done est. percent": (
                        (  # ex: 0/1.00 (0.0000)
                            f"{pixels_done(nside)}/{(n_sent_recos(nside)):.2f} "
                            f"({pixels_done(nside) / (n_sent_recos(nside)):.4f})"
                        )
                        if nside in self._n_sent_by_nside
                        else "N/A"
                    ),
                    "generated total": n_sent_recos(nside),
                    "initial approx. total": f"{self.estimated_total_nside_recos[nside] / self.n_posvar:2f}",
                },
            }

        # see when we reached X% done
        predicted_total = self.predicted_total_recos()
        timeline = {}
        for i in [-1.0] + cfg.REPORTER_TIMELINE_PERCENTAGES:
            if i == -1.0:
                index = 0  # make sure it's the first to avoid any floating point error
                # now use the amount of decimal places used by most precise % (or 4)
                decimal_places = max(
                    [
                        str(num)[::-1].find(".")
                        for num in cfg.REPORTER_TIMELINE_PERCENTAGES
                    ]
                    + [4],
                )
                name = f"{1 / predicted_total:.{decimal_places}f}"
            else:
                # round up b/c it's when scan *reached* X%
                index = math.ceil(predicted_total * i) - 1
                name = str(i)
            try:
                when = self.worker_stats_collection.aggregate._on_server_roundtrip_ends[
                    index
                ]
                timeline[name] = str(
                    dt.timedelta(seconds=int(when - self.global_start))
                )
            except IndexError:  # have not reached that point yet
                pass

        return {
            "nsides": tallies_by_nside,
            "total pixels": sum(v["pixels"]["done"] for v in tallies_by_nside.values()),
            "total recos": self.worker_stats_collection.total_ct,
            "est. scan percent (recos)": (
                f"{self.worker_stats_collection.total_ct}/{predicted_total} "
                f"({self.worker_stats_collection.total_ct / predicted_total:.4f})"
            ),
            "est. scan timeline": timeline,
        }

    async def after_computing_report(self) -> SkyScanResult:
        """Get, log, and send final results to SkyDriver."""
        self._check_call_order(self.after_computing_report)

        self.is_event_scan_done = True
        result = await self._send_result()
        await self._send_progress(
            "The Skymap Scanner has finished.",
        )
        return result

    async def _send_progress(
        self,
        summary_msg: str,
        epilogue_msg: str = "",
    ) -> None:
        """Send progress to SkyDriver (if the connection is established)."""
        progress = {
            "summary": summary_msg,
            "epilogue": epilogue_msg,
            "tallies": self._get_tallies(),
            "processing_stats": self._get_processing_progress(),
            "predictive_scanning_threshold": self.predictive_scanning_threshold,
            "last_updated": str(dt.datetime.fromtimestamp(int(time.time()))),
            # fields new to skydriver v2
            "start": int(self.global_start),
            "end": int(time.time()) if self.is_event_scan_done else None,
        }
        scan_metadata = {
            "scan_id": ENV.SKYSCAN_SKYDRIVER_SCAN_ID,
            "nside_progression": self.nside_progression,
            "position_variations": self.n_posvar,
        }

        LOGGER.info(pyobj_to_string_repr(progress))

        body = {
            "progress": progress,
            "event_metadata": dc.asdict(self.event_metadata),
            "scan_metadata": scan_metadata,
        }

        # skydriver
        sd_args = dict(
            method="PATCH",
            path=f"/scan/{ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/manifest",
            args=body,
        )
        if not self.is_event_scan_done and self.skydriver_rc_nonurgent:
            await nonurgent_request(self.skydriver_rc_nonurgent, sd_args)
        elif self.is_event_scan_done and self.skydriver_rc_urgent:
            await self.skydriver_rc_urgent.request(**sd_args)

        # output file
        if self.output_dir:
            fpath = self.output_dir / "scan-manifest.json"
            with open(fpath, "w") as f:
                json.dump(body, f, indent=4)
            LOGGER.info(f"Manifest File (scan progress + metadata): {fpath}")

    async def _send_result(self) -> SkyScanResult:
        """Send result to SkyDriver (if the connection is established)."""
        result = self._get_result()
        serialized = result.serialize()

        LOGGER.debug(  # don't log HUGE string
            f"Result info (# pixels per nside): {[(k, len(v)) for k, v in result.result.items()]}"
        )

        # skydriver
        body = {"skyscan_result": serialized, "is_final": self.is_event_scan_done}
        sd_args = dict(
            method="PUT",
            path=f"/scan/{ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/result",
            args=body,
        )
        if not self.is_event_scan_done and self.skydriver_rc_nonurgent:
            await nonurgent_request(self.skydriver_rc_nonurgent, sd_args)
        elif self.is_event_scan_done and self.skydriver_rc_urgent:
            await self.skydriver_rc_urgent.request(**sd_args)

        # output file
        if self.output_dir and result.result:  # don't write empty result to files
            npz_fpath = result.to_npz(self.event_metadata, self.output_dir)
            json_fpath = result.to_json(self.event_metadata, self.output_dir)
            LOGGER.info(f"Result Files: {npz_fpath}, {json_fpath}")

        return result
