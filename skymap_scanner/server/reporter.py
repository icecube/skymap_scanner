"""Contains a class for reporting progress and result for a scan."""

# pylint: disable=import-error


import bisect
import dataclasses as dc
import datetime as dt
import itertools
import statistics
import time
from typing import Any, Callable, Dict, List, Optional

from rest_tools.client import RestClient

from .. import config as cfg
from ..utils import pixelreco
from ..utils.event_tools import EventMetadata
from ..utils.scan_result import ScanResult
from ..utils.utils import pyobj_to_string_repr
from . import LOGGER

StrDict = Dict[str, Any]


class WorkerStats:
    """Holds rates and stats for the per-reco/worker level."""

    def __init__(self) -> None:
        self.start = float("inf")
        self.end = float("-inf")

        self.rates: List[float] = []
        # self.rates.sort()  # will make stats calls much faster

        self.fastest = lambda: min(self.rates)
        self.slowest = lambda: max(self.rates)

        # Fast, floating point arithmetic mean.
        self.fmean = lambda: statistics.fmean(self.rates)
        self.mean = self.fmean  # use fmean since these are floats
        # Median (middle value) of data.
        self.median = lambda: statistics.median(self.rates)

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

    def update(self, new_rate: float, start: float, end: float) -> "WorkerStats":
        bisect.insort(self.rates, new_rate)
        self.start = min(self.start, start)
        self.end = max(self.end, end)
        return self

    @staticmethod
    def _make_summary(
        mean: float,
        median: float,
        slowest: float,
        fastest: float,
        start: float,
        end: float,
        nrates: int,
    ) -> Dict[str, str]:
        return {
            "mean reco (worker time)": str(dt.timedelta(seconds=int(mean))),
            "median reco (worker time)": str(dt.timedelta(seconds=int(median))),
            "slowest reco (worker time)": str(dt.timedelta(seconds=int(slowest))),
            "fastest reco (worker time)": str(dt.timedelta(seconds=int(fastest))),
            "start time (first reco)": str(dt.datetime.fromtimestamp(int(start))),
            "end time (last reco)": str(dt.datetime.fromtimestamp(int(end))),
            "runtime (wall time)": str(dt.timedelta(seconds=int(end - start))),
            "mean reco (scanner wall time)": str(
                dt.timedelta(seconds=int((end - start) / nrates))
            ),
        }

    def get_summary(self) -> Dict[str, str]:
        return self._make_summary(
            self.mean(),  # type: ignore[no-untyped-call]
            self.median(),  # type: ignore[no-untyped-call]
            self.slowest(),  # type: ignore[no-untyped-call]
            self.fastest(),  # type: ignore[no-untyped-call]
            self.start,
            self.end,
            len(self.rates),
        )


class WorkerStatsCollection:
    """A performant collection of WorkerStats instances."""

    def __init__(self) -> None:
        self._worker_stats_by_nside: Dict[int, WorkerStats] = {}

    @property
    def total_ct(self) -> int:
        return sum(len(w.rates) for w in self._worker_stats_by_nside.values())

    @property
    def first_reco_start(self) -> float:
        return min(w.start for w in self._worker_stats_by_nside.values())

    def update(
        self,
        nside: int,
        rate: float,
        pixreco_start: float,
        pixreco_end: float,
    ) -> int:
        """Return reco-count of nside's list."""
        try:
            worker_stats = self._worker_stats_by_nside[nside]
        except KeyError:
            worker_stats = self._worker_stats_by_nside[nside] = WorkerStats()
        worker_stats.update(rate, pixreco_start, pixreco_end)
        return len(worker_stats.rates)

    def _get_aggregate_summary(self) -> Dict[str, str]:
        total_nrates = self.total_ct
        instances = self._worker_stats_by_nside.values()
        return WorkerStats._make_summary(
            sum(i.mean() * len(i.rates) for i in instances) / total_nrates,  # type: ignore[no-untyped-call]
            statistics.median(itertools.chain(i.rates for i in instances)),
            max(i.slowest() for i in instances),  # type: ignore[no-untyped-call]
            min(i.fastest() for i in instances),  # type: ignore[no-untyped-call]
            min(i.start for i in instances),
            max(i.end for i in instances),
            total_nrates,
        )

    def get_summary(self) -> StrDict:
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

        self._n_pixreco_expected: Optional[int] = None

        self.min_nside = min_nside  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        self.max_nside = max_nside  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        self.skydriver_rc = skydriver_rc
        self.event_metadata = event_metadata

        # all set by calling initial_report()
        self.last_time_reported = 0.0
        self.last_time_reported_skymap = 0.0
        self.worker_stats_collection: WorkerStatsCollection = WorkerStatsCollection()

        self._call_order = {
            "current_previous": {  # current_fucntion: previous_fucntion(self.rates)
                self.precomputing_report: [None],
                self.start_computing: [self.precomputing_report],
                self.record_pixreco: [self.start_computing, self.record_pixreco],
                self.final_computing_report: [self.record_pixreco],
                self.after_computing_report: [self.final_computing_report],
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

    async def start_computing(self, n_pixreco_expected: int) -> None:
        """Send an initial report/log/plot.

        Arguments:
            `n_pixreco_expected`
                - number of expected pixel-recos
            `n_posvar`
                - number of position variations per pixel
        """
        self._check_call_order(self.start_computing)
        self.n_pixreco_expected = n_pixreco_expected
        await self._make_reports_if_needed(
            bypass_timers=True,
            summary_msg="The Skymap Scanner has sent out pixels and is waiting to receive recos.",
        )

    @property
    def n_pixreco_expected(self) -> int:
        if self._n_pixreco_expected is None:
            raise RuntimeError(
                f"'self._n_pixreco_expected' is None (did you forget to call {self.start_computing}?)"
            )
        return self._n_pixreco_expected

    @n_pixreco_expected.setter
    def n_pixreco_expected(self, val: int) -> None:
        if val <= 0:
            raise ValueError(f"n_pixreco_expected is not positive: {val}")
        self._n_pixreco_expected = val

    async def record_pixreco(
        self,
        pixreco_nside: int,
        pixreco_start: float,
        pixreco_end: float,
    ) -> None:
        """Send reports/logs/plots if needed."""
        self._check_call_order(self.record_pixreco)
        rate = pixreco_end - pixreco_start

        # update stats
        nside_ct = self.worker_stats_collection.update(
            pixreco_nside,
            rate,
            pixreco_start,
            pixreco_end,
        )

        # make report(s)
        if nside_ct == 1:
            # always report the first received pixreco so we know things are rolling
            await self._make_reports_if_needed(bypass_timers=True)
        else:
            await self._make_reports_if_needed()

    async def _make_reports_if_needed(
        self,
        bypass_timers: bool = False,
        summary_msg: str = "The Skymap Scanner is busy scanning pixels.",
    ) -> None:
        """Send reports/logs/plots if needed."""
        LOGGER.info(
            f"Collected: {self.worker_stats_collection.total_ct}/{self.n_pixreco_expected} ({self.worker_stats_collection.total_ct/self.n_pixreco_expected})"
        )

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
            elif self.worker_stats_collection.total_ct != self.n_pixreco_expected:
                epilogue_msg = f"I will report back again in {cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC} seconds."
            else:
                epilogue_msg = ""
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

        if not self.worker_stats_collection:  # still waiting
            return proc_stats

        # stats now that we have reco(s)
        elapsed_reco_walltime = (
            time.time() - self.worker_stats_collection.first_reco_start
        )
        prior_processing_secs = (
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
                "prior processing": str(
                    dt.timedelta(seconds=int(prior_processing_secs))
                ),
                "reco runtime": str(dt.timedelta(seconds=int(elapsed_reco_walltime))),
                "reco runtime + prior processing": str(
                    dt.timedelta(
                        seconds=int(elapsed_reco_walltime + prior_processing_secs)
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
            # NOTE: this is a simple mean, may want to visit more sophisticated methods
            secs_predicted = elapsed_reco_walltime / (
                self.worker_stats_collection.total_ct / self.n_pixreco_expected
            )
            proc_stats["predictions"] = {
                "time left": str(
                    dt.timedelta(seconds=int(secs_predicted - elapsed_reco_walltime))
                ),
                "total runtime at finish": str(
                    dt.timedelta(seconds=int(secs_predicted + prior_processing_secs))
                ),
            }

        return proc_stats

    def _get_tallies(self) -> StrDict:
        """Get a multi-dict progress report of the nsides_dict's contents."""
        saved = {}
        if self.nsides_dict:
            for nside in sorted(self.nsides_dict):  # sorted by nside
                saved[nside] = len(self.nsides_dict[nside])

        # TODO: add denominator ^^^^
        # 'remaining': {
        #     # counts are downplayed using 'amount remaining' so we never report percent done
        #     'percent': ##,
        #     'pixels': ###/###,
        #     'recos': ####/####,
        # },

        # TODO: remove for #84
        this_iteration = {}
        if self._n_pixreco_expected is not None:
            this_iteration = {
                "percent": (
                    self.worker_stats_collection.total_ct / self.n_pixreco_expected
                )
                * 100,
                "pixels": f"{self.worker_stats_collection.total_ct/self.n_posvar}/{self.n_pixreco_expected/self.n_posvar}",
                "recos": f"{self.worker_stats_collection.total_ct}/{self.n_pixreco_expected}",
            }

        return {
            "by_nside": saved,
            "total": sum(s for s in saved.values()),  # total completed pixels
            # TODO: for #84: uncomment b/c this will now be scan-wide total & remove 'this iteration' dict
            # 'total_recos': self.worker_stats_by_nside.total_ct,
            "this_iteration": this_iteration,  # TODO: remove for #84
        }

    async def final_computing_report(self) -> None:
        """Check if all the pixel-recos were received & make a final report."""
        self._check_call_order(self.final_computing_report)
        if not self.worker_stats_collection.total_ct:
            raise RuntimeError("No pixel-reconstructions were ever received.")

        if self.worker_stats_collection.total_ct != self.n_pixreco_expected:
            raise RuntimeError(
                f"Not all pixel-reconstructions were received: "
                f"{self.worker_stats_collection.total_ct}/{self.n_pixreco_expected} ({self.worker_stats_collection.total_ct/self.n_pixreco_expected})"
            )

        await self._make_reports_if_needed(
            bypass_timers=True,
            summary_msg="The Skymap Scanner has finished this iteration of pixels.",
        )

    async def after_computing_report(
        self,
        total_n_pixreco_expected: int,  # TODO: remove for https://github.com/icecube/skymap_scanner/issues/84
    ) -> ScanResult:
        """Get, log, and send final results to SkyDriver."""
        self._check_call_order(self.after_computing_report)
        self.is_event_scan_done = True
        result = await self._send_result()
        await self._send_progress(
            "The Skymap Scanner has finished.",
            total_n_pixreco_expected=total_n_pixreco_expected,  # TODO: remove for https://github.com/icecube/skymap_scanner/issues/84
        )
        return result

    async def _send_progress(
        self,
        summary_msg: str,
        epilogue_msg: str = "",
        total_n_pixreco_expected: int = None,  # TODO: remove for https://github.com/icecube/skymap_scanner/issues/84
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

        if total_n_pixreco_expected:
            # TODO: remove for https://github.com/icecube/skymap_scanner/issues/84
            # see _get_tallies()
            progress["tallies"]["total_recos"] = total_n_pixreco_expected

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
