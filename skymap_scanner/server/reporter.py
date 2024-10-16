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
    ) -> None:
        self.on_worker_runtimes = on_worker_runtimes
        self.on_worker_runtimes.sort()  # speed up stats
        #
        self.on_server_roundtrips = on_server_roundtrips
        self.on_server_roundtrips.sort()  # speed up stats
        #
        self.on_server_roundtrip_starts: List[float] = on_server_roundtrip_starts
        self.on_server_roundtrip_starts.sort()  # speed up stats
        self.on_server_first_roundtrip_start = lambda: min(
            self.on_server_roundtrip_starts
        )
        #
        self.on_server_roundtrip_ends = on_server_roundtrip_ends
        self.on_server_roundtrip_ends.sort()  # speed up stats
        self.on_server_last_roundtrip_end = lambda: max(self.on_server_roundtrip_ends)

        self.fastest_worker = lambda: min(self.on_worker_runtimes)
        self.fastest_roundtrip = lambda: min(self.on_server_roundtrips)

        self.slowest_worker = lambda: max(self.on_worker_runtimes)
        self.slowest_roundtrip = lambda: max(self.on_server_roundtrips)

        # Fast, floating point arithmetic mean.
        self.mean_worker = lambda: statistics.fmean(self.on_worker_runtimes)
        self.mean_roundtrip = lambda: statistics.fmean(self.on_server_roundtrips)

        # Median (middle value) of data.
        self.median_worker = lambda: float(statistics.median(self.on_worker_runtimes))
        self.median_roundtrip = lambda: float(
            statistics.median(self.on_server_roundtrips)
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
    ) -> "WorkerStats":
        """Insert the runtime and recalculate round-trip start/end times."""
        bisect.insort(
            self.on_worker_runtimes,
            on_worker_runtime,
        )
        bisect.insort(
            self.on_server_roundtrips,
            on_server_roundtrip_end - on_server_roundtrip_start,
        )
        bisect.insort(
            self.on_server_roundtrip_starts,
            on_server_roundtrip_start,
        )
        bisect.insort(
            self.on_server_roundtrip_ends,
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
                            / len(self.on_worker_runtimes)
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

    def on_server_recent_reco_per_sec_rate(self, window_size: int) -> float:
        """The reco/sec rate from server pov within a moving window."""

        # look at a window, so don't use the first start time
        try:
            # psst, we know that this list is sorted, ascending
            nth_most_recent_start = self.aggregate.on_server_roundtrip_starts[
                -window_size
            ]
            n_recos = window_size
        except IndexError:
            nth_most_recent_start = self.aggregate.on_server_first_roundtrip_start()
            n_recos = len(self.aggregate.on_worker_runtimes)

        return n_recos / (
            self.aggregate.on_server_last_roundtrip_end() - nth_most_recent_start
        )

    def ct_by_nside(self, nside: int) -> int:
        """Get length per given nside."""
        try:
            return len(self._worker_stats_by_nside[nside].on_worker_runtimes)
        except KeyError:
            return 0

    @property
    def total_ct(self) -> int:
        """O(n) b/c len is O(1), n < 10."""
        return sum(
            len(w.on_worker_runtimes) for w in self._worker_stats_by_nside.values()
        )

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
            )
        except KeyError:
            worker_stats = self._worker_stats_by_nside[nside] = WorkerStats(
                on_worker_runtimes=[on_worker_runtime],
                on_server_roundtrips=[
                    on_server_roundtrip_end - on_server_roundtrip_start
                ],
                on_server_roundtrip_starts=[on_server_roundtrip_start],
                on_server_roundtrip_ends=[on_server_roundtrip_end],
            )
        return len(worker_stats.on_worker_runtimes)

    @property
    def aggregate(self) -> WorkerStats:
        """An aggregate (`WorkerStats` obj) of all recos (all nsides)."""
        if not self._aggregate:
            instances = self._worker_stats_by_nside.values()
            if not instances:
                return WorkerStats([], [], [], [])
            self._aggregate = WorkerStats(
                on_worker_runtimes=list(
                    itertools.chain(*[i.on_worker_runtimes for i in instances])
                ),
                on_server_roundtrips=list(
                    itertools.chain(*[i.on_server_roundtrips for i in instances])
                ),
                on_server_roundtrip_starts=list(
                    itertools.chain(*[i.on_server_roundtrip_starts for i in instances])
                ),
                on_server_roundtrip_ends=list(
                    itertools.chain(*[i.on_server_roundtrip_ends for i in instances])
                ),
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

        self._n_sent_by_nside: Dict[int, int] = {}

        if not cfg.ENV.SKYSCAN_SKYDRIVER_ADDRESS:
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

    def increment_sent_ct(self, nside: int, increment: int = 1) -> None:
        """Increment the number sent by nside."""
        try:
            self._n_sent_by_nside[nside] += increment
        except KeyError:
            self._n_sent_by_nside[nside] = increment

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
            current_time - self.last_time_reported
            > cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC
        ):
            self.last_time_reported = current_time
            if self.worker_stats_collection.total_ct == 0:
                epilogue_msg = "I will report back when I start getting recos."
            else:
                epilogue_msg = (
                    f"I will report back again in "
                    f"{cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC} seconds if I have an update."
                )
            await self._send_progress(summary_msg, epilogue_msg)

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported_skymap
            > cfg.ENV.SKYSCAN_RESULT_INTERVAL_SEC
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

        estimates = self.nside_progression.n_recos_by_nside_lowerbound(self.n_posvar)
        estimates_with_sents = sum(
            self._n_sent_by_nside.get(nside, estimates[nside])
            for nside in self.nside_progression
        )
        # estimates-sum SHOULD be a lower bound, but if estimates_with_sents
        #   is less than there will be more recos sent in the future
        return max(estimates_with_sents, sum(estimates.values()))

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
                self.worker_stats_collection.on_server_recent_reco_per_sec_rate(
                    window_size=int(
                        self.worker_stats_collection.total_ct
                        * cfg.ENV.SKYSCAN_PROGRESS_RUNTIME_PREDICTION_WINDOW_RATIO
                    )
                )
                / n_recos_left  # (recos/sec)*(1/recos) -> sec
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
            }

        return proc_stats

    def _get_tallies(self) -> StrDict:
        """Get a multi-dict progress report of the nsides_dict's contents."""

        reco_lowerbounds = self.nside_progression.n_recos_by_nside_lowerbound(
            self.n_posvar
        )

        def recos_percent_string(nside: int) -> str:
            if nside not in self._n_sent_by_nside:  # hasn't been sent
                return f"N/A ({reco_lowerbounds[nside]} predicted)"
            return (
                f"{self.worker_stats_collection.ct_by_nside(nside)}/{self._n_sent_by_nside[nside]} "
                f"({self.worker_stats_collection.ct_by_nside(nside) / self._n_sent_by_nside[nside]:.4f})"
            )

        def pixels_done(nside: int) -> int:
            return len(self.nsides_dict.get(nside, []))

        def pixels_percent_string(nside: int) -> str:
            if nside not in self._n_sent_by_nside:  # hasn't been sent
                return f"N/A ({int(reco_lowerbounds[nside]/self.n_posvar)} predicted)"
            # only finished pixels
            done = int(self._n_sent_by_nside[nside] / self.n_posvar)
            return f"{pixels_done(nside)}/{done} ({pixels_done(nside) / done:.4f})"

        by_nside = {}
        # get done counts & percentages (estimates for future nsides)
        for nside in self.nside_progression:  # sorted by nside
            by_nside[nside] = {
                "done": pixels_done(nside),  # only finished pixels
                "est. percent": pixels_percent_string(nside),
                "est. percent (recos)": recos_percent_string(nside),
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
                when = self.worker_stats_collection.aggregate.on_server_roundtrip_ends[
                    index
                ]
                timeline[name] = str(
                    dt.timedelta(seconds=int(when - self.global_start))
                )
            except IndexError:  # have not reached that point yet
                pass

        return {
            "nsides": by_nside,
            # total completed pixels
            "total pixels": sum(v["done"] for v in by_nside.values()),
            "total recos": self.worker_stats_collection.total_ct,
            "est. scan percent": (
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
        }
        scan_metadata = {
            "scan_id": cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID,
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
            path=f"/scan/{cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/manifest",
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
            path=f"/scan/{cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID}/result",
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
