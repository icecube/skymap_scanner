"""Contains a class for reporting progress and result for a scan."""

# pylint: disable=import-error


import bisect
import dataclasses as dc
import datetime as dt
import itertools
import statistics
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from rest_tools.client import RestClient

from .. import config as cfg
from ..utils import pixelreco
from ..utils.event_tools import EventMetadata
from ..utils.scan_result import ScanResult
from ..utils.utils import estimated_nside_n_recos, pyobj_to_string_repr
from . import LOGGER

StrDict = Dict[str, Any]


class WorkerStats:
    """Holds stats for the per-reco/worker level."""

    def __init__(self) -> None:
        self.roundtrip_start = float("inf")
        self.roundtrip_end = float("-inf")

        self.runtimes: List[float] = []
        # self.runtimes.sort()  # will make stats calls much faster

        self.fastest = lambda: min(self.runtimes)
        self.slowest = lambda: max(self.runtimes)

        # Fast, floating point arithmetic mean.
        self.fmean = lambda: statistics.fmean(self.runtimes)
        self.mean = self.fmean  # use fmean since these are floats
        # Median (middle value) of data.
        self.median = lambda: float(statistics.median(self.runtimes))

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
        runtime: float,
        roundtrip_start: float,
        roundtrip_end: float,
    ) -> "WorkerStats":
        """Insert the runtime and recalculate round-trip start/end times."""
        bisect.insort(self.runtimes, runtime)
        self.roundtrip_start = min(self.roundtrip_start, roundtrip_start)
        self.roundtrip_end = max(self.roundtrip_end, roundtrip_end)
        return self

    @staticmethod
    def _make_summary(
        mean: float,
        median: float,
        slowest: float,
        fastest: float,
        roundtrip_start: float,
        roundtrip_end: float,
        count: int,
    ) -> Dict[str, str]:
        return {
            "mean reco (worker time)": str(dt.timedelta(seconds=int(mean))),
            "median reco (worker time)": str(dt.timedelta(seconds=int(median))),
            "slowest reco (worker time)": str(dt.timedelta(seconds=int(slowest))),
            "fastest reco (worker time)": str(dt.timedelta(seconds=int(fastest))),
            "start time": str(dt.datetime.fromtimestamp(int(roundtrip_start))),
            "end time": str(dt.datetime.fromtimestamp(int(roundtrip_end))),
            "runtime (wall time)": str(
                dt.timedelta(seconds=int(roundtrip_end - roundtrip_start))
            ),
            "mean reco (scanner wall time)": str(
                dt.timedelta(seconds=int((roundtrip_end - roundtrip_start) / count))
            ),
        }

    def get_summary(self) -> Dict[str, str]:
        """Make a human-readable dict summary of the instance."""
        return self._make_summary(
            self.mean(),  # type: ignore[no-untyped-call]
            self.median(),  # type: ignore[no-untyped-call]
            self.slowest(),  # type: ignore[no-untyped-call]
            self.fastest(),  # type: ignore[no-untyped-call]
            self.roundtrip_start,
            self.roundtrip_end,
            len(self.runtimes),
        )


class WorkerStatsCollection:
    """A performant collection of WorkerStats instances."""

    def __init__(self) -> None:
        self._worker_stats_by_nside: Dict[int, WorkerStats] = {}

    @property
    def total_ct(self) -> int:
        # O(n) b/c len is O(1), n < 10
        return sum(len(w.runtimes) for w in self._worker_stats_by_nside.values())

    @property
    def first_reco_start(self) -> float:
        # O(n), n < 10
        return min(w.roundtrip_start for w in self._worker_stats_by_nside.values())

    def update(
        self,
        nside: int,
        pixreco_runtime: float,
        roundtrip_start: float,
        roundtrip_end: float,
    ) -> int:
        """Return reco-count of nside's list after updating."""
        try:
            worker_stats = self._worker_stats_by_nside[nside]
        except KeyError:
            worker_stats = self._worker_stats_by_nside[nside] = WorkerStats()
        worker_stats.update(pixreco_runtime, roundtrip_start, roundtrip_end)
        return len(worker_stats.runtimes)

    def _get_aggregate_summary(self) -> Dict[str, str]:
        instances = self._worker_stats_by_nside.values()
        return WorkerStats._make_summary(
            sum(i.mean() * len(i.runtimes) for i in instances) / self.total_ct,  # type: ignore[no-untyped-call]
            statistics.median(itertools.chain(*[i.runtimes for i in instances])),
            max(i.slowest() for i in instances),  # type: ignore[no-untyped-call]
            min(i.fastest() for i in instances),  # type: ignore[no-untyped-call]
            min(i.roundtrip_start for i in instances),
            max(i.roundtrip_end for i in instances),
            self.total_ct,
        )

    def get_summary(self) -> StrDict:
        """Make human-readable dict summaries for all nsides & an aggregate."""
        dicto: StrDict = self._get_aggregate_summary()
        for nside, worker_stats in self._worker_stats_by_nside.items():
            dicto[f"nside-{nside}"] = worker_stats.get_summary()
        return dicto


class Reporter:
    """Manage means for reporting progress & results during/after the scan."""

    def __init__(
        self,
        scan_id: str,
        global_start_time: float,
        nsides_dict: pixelreco.NSidesDict,
        n_posvar: int,
        min_nside: int,  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        max_nside: int,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        skydriver_rc: Optional[RestClient],
        event_metadata: EventMetadata,
    ) -> None:
        """
        Arguments:
            `scan_id`
                - the unique id of this scan
            `global_start_time`
                - the start time (epoch) of the entire scan
            `nsides_dict`
                - the nsides_dict
            `n_posvar`
                - number of position variations per pixel
            `min_nside`
                - min nside value
            `max_nside`
                - max nside value
            `skydriver_rc`
                - a connection to the SkyDriver REST interface
            `event_metadata`
                - a collection of metadata about the event

        Environment Variables:
            `SKYSCAN_PROGRESS_INTERVAL_SEC`
                - produce a progress report with this interval
            `SKYSCAN_RESULT_INTERVAL_SEC`
                - produce a (partial) skymap result with this interval
        """
        self.is_event_scan_done = False

        self.scan_id = scan_id
        self.global_start = global_start_time
        self.nsides_dict = nsides_dict

        if n_posvar <= 0:
            raise ValueError(f"n_posvar is not positive: {n_posvar}")
        self.n_posvar = n_posvar

        self.min_nside = min_nside  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        self.max_nside = max_nside  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        # TODO: remove HARDCODED estimate along with ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        nsides: List[Tuple[int, int]] = [(8, 12), (64, 12), (512, 24)]
        if min_nside == 1 and max_nside == 1:
            nsides = [(1, 12)]
        self._estimated_nside_n_recos = estimated_nside_n_recos(nsides, self.n_posvar)

        self.skydriver_rc = skydriver_rc
        self.event_metadata = event_metadata

        # all set by calling initial_report()
        self.last_time_reported = 0.0
        self.last_time_reported_skymap = 0.0
        self.worker_stats_collection: WorkerStatsCollection = WorkerStatsCollection()

        self._call_order = {
            "current_previous": {  # current_fucntion: previous_fucntion
                self.precomputing_report: [None],
                self.record_pixreco: [self.precomputing_report, self.record_pixreco],
                self.after_computing_report: [self.record_pixreco],
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

    async def precomputing_report(self) -> None:
        """Make a report before ANYTHING is computed."""
        self._check_call_order(self.precomputing_report)
        await self._send_progress(summary_msg="The Skymap Scanner has started up.")

    async def record_pixreco(
        self,
        pixreco_nside: int,
        pixreco_runtime: float,
        roundtrip_start: float,
        roundtrip_end: float,
    ) -> None:
        """Send reports/logs/plots if needed."""
        self._check_call_order(self.record_pixreco)

        # update stats
        nside_ct = self.worker_stats_collection.update(
            pixreco_nside,
            pixreco_runtime,
            roundtrip_start,
            roundtrip_end,
        )

        # make report(s)
        if nside_ct == 1:
            # always report the first received pixreco so we know things are rolling
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
                epilogue_msg = (
                    "I will report back when I start getting pixel-reconstructions."
                )
            else:
                epilogue_msg = f"I will report back again in {cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC} seconds."
            await self._send_progress(summary_msg, epilogue_msg)

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported_skymap
            > cfg.ENV.SKYSCAN_RESULT_INTERVAL_SEC
        ):
            self.last_time_reported_skymap = current_time
            await self._send_result()

    def _get_result(self) -> ScanResult:
        """Get ScanResult."""
        return ScanResult.from_nsides_dict(self.nsides_dict, self.event_metadata)

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
        elapsed_reco_walltime = (
            time.time() - self.worker_stats_collection.first_reco_start
        )
        startup_runtime = (
            self.worker_stats_collection.first_reco_start - self.global_start
        )
        proc_stats["start"].update(
            {
                "reco start": str(
                    dt.datetime.fromtimestamp(
                        int(self.worker_stats_collection.first_reco_start)
                    )
                ),
            }
        )
        proc_stats["runtime"].update(
            {
                "startup runtime": str(dt.timedelta(seconds=int(startup_runtime))),
                "reco runtime": str(dt.timedelta(seconds=int(elapsed_reco_walltime))),
                "reco runtime + startup runtime": str(
                    dt.timedelta(seconds=int(elapsed_reco_walltime + startup_runtime))
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
            # NOTE: this is a simple mean, may want to visit more sophisticated methods
            secs_predicted = elapsed_reco_walltime / (
                self.worker_stats_collection.total_ct
                / sum(self._estimated_nside_n_recos.values())
            )
            proc_stats["predictions"] = {
                "time left": str(
                    dt.timedelta(seconds=int(secs_predicted - elapsed_reco_walltime))
                ),
                "total runtime at finish": str(
                    dt.timedelta(seconds=int(secs_predicted + startup_runtime))
                ),
                "total # of reconstructions": sum(
                    self._estimated_nside_n_recos.values()
                ),
                "end": str(
                    dt.datetime.fromtimestamp(
                        int(time.time() + (secs_predicted - elapsed_reco_walltime))
                    )
                ),
            }

        return proc_stats

    def _get_tallies(self) -> StrDict:
        """Get a multi-dict progress report of the nsides_dict's contents."""
        saved = {}
        if self.nsides_dict:
            for nside in sorted(self.nsides_dict):  # sorted by nside
                n_done = len(self.nsides_dict[nside])
                saved[nside] = {
                    "done": n_done,
                    "est. percent": (
                        f"{n_done}/{self._estimated_nside_n_recos[nside]} "
                        f"({n_done / self._estimated_nside_n_recos[nside]:.2f})"
                    ),
                }

        return {
            "by_nside": saved,
            "total": sum(v["done"] for v in saved.values()),  # total completed pixels
            "total_recos": self.worker_stats_collection.total_ct,
        }

    async def after_computing_report(self) -> ScanResult:
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
        }
        scan_metadata = {
            "scan_id": self.scan_id,
            "min_nside": self.min_nside,  # TODO: replace with nsides (https://github.com/icecube/skymap_scanner/issues/79)
            "max_nside": self.max_nside,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
            "position_variations": self.n_posvar,
        }

        LOGGER.info(pyobj_to_string_repr(progress))
        if not self.skydriver_rc:
            return

        body = {
            "progress": progress,
            "event_metadata": dc.asdict(self.event_metadata),
            "scan_metadata": scan_metadata,
        }
        await self.skydriver_rc.request("PATCH", f"/scan/manifest/{self.scan_id}", body)

    async def _send_result(self) -> ScanResult:
        """Send result to SkyDriver (if the connection is established)."""
        result = self._get_result()
        serialized = result.serialize()

        LOGGER.info(pyobj_to_string_repr(serialized))
        if not self.skydriver_rc:
            return result

        body = {"skyscan_result": serialized, "is_final": self.is_event_scan_done}
        await self.skydriver_rc.request("PUT", f"/scan/result/{self.scan_id}", body)

        return result
