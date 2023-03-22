"""Contains a class for reporting progress and result for a scan."""

# pylint: disable=import-error

# fmt:quotes-ok

import dataclasses as dc
import datetime as dt
import time
from typing import Any, Callable, Dict, Optional

from rest_tools.client import RestClient

from .. import config as cfg
from ..utils import pixelreco
from ..utils.event_tools import EventMetadata
from ..utils.scan_result import ScanResult
from ..utils.utils import pyobj_to_string_repr
from . import LOGGER

StrDict = Dict[str, Any]


@dc.dataclass
class WorkerRates:
    """Simple class that holds info rates at the per-reco/worker level."""

    fastest: float
    slowest: float
    average: float


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
        self.global_start_time = global_start_time
        self.nsides_dict = nsides_dict

        if n_posvar <= 0:
            raise ValueError(f"n_posvar is not positive: {n_posvar}")
        self.n_posvar = n_posvar

        self._n_pixreco_expected: Optional[int] = None
        self.pixreco_ct = 0

        self.min_nside = min_nside  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        self.max_nside = max_nside  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        self.skydriver_rc = skydriver_rc
        self.event_metadata = event_metadata

        # all set by calling initial_report()
        self.last_time_reported = 0.0
        self.last_time_reported_skymap = 0.0
        self.scan_start = 0.0
        self.worker_rates = WorkerRates(fastest=0, slowest=0, average=0)

        self._call_order = {
            'current_previous': {  # current_fucntion: previous_fucntion(s)
                self.precomputing_report: [None],
                self.start_computing: [
                    self.precomputing_report,
                    self.final_computing_report,  # TODO: remove for #84
                ],
                self.record_pixreco: [self.start_computing, self.record_pixreco],
                self.final_computing_report: [self.record_pixreco],
                self.after_computing_report: [self.final_computing_report],
            },
            'last_called': None,
        }

    def _check_call_order(self, current: Callable) -> None:  # type: ignore[type-arg]
        """Make sure we're calling everything in order."""
        if (
            self._call_order['last_called']  # type: ignore[operator]
            not in self._call_order['current_previous'][current]  # type: ignore[index]
        ):
            RuntimeError(f"Out of order execution: {self._call_order['last_called']=}")
        self._call_order['last_called'] = current  # type: ignore[assignment]

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
        self.pixreco_ct = 0
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

    async def record_pixreco(self, pixreco_start: float, pixreco_end: float) -> None:
        """Send reports/logs/plots if needed."""
        self._check_call_order(self.record_pixreco)
        self.pixreco_ct += 1
        rate = pixreco_end - pixreco_start

        if self.pixreco_ct == 1:
            self.scan_start = pixreco_start
            self.worker_rates = WorkerRates(fastest=rate, slowest=rate, average=rate)
            # always report the first received pixreco so we know things are rolling
            await self._make_reports_if_needed(bypass_timers=True)
        else:
            self.scan_start = min(self.scan_start, pixreco_start)
            self.worker_rates = WorkerRates(
                fastest=min(self.worker_rates.fastest, rate),
                slowest=max(self.worker_rates.slowest, rate),
                average=(
                    ((self.worker_rates.average * (self.pixreco_ct - 1)) + rate)
                    / self.pixreco_ct
                ),
            )
            await self._make_reports_if_needed()

    async def _make_reports_if_needed(
        self,
        bypass_timers: bool = False,
        summary_msg: str = "The Skymap Scanner is busy scanning pixels.",
    ) -> None:
        """Send reports/logs/plots if needed."""
        LOGGER.info(
            f"Collected: {self.pixreco_ct}/{self.n_pixreco_expected} ({self.pixreco_ct/self.n_pixreco_expected})"
        )

        # check if we need to send a report to the logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported
            > cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC
        ):
            self.last_time_reported = current_time
            if self.pixreco_ct == 0:
                epilogue_msg = (
                    "I will report back when I start getting pixel-reconstructions."
                )
            elif self.pixreco_ct != self.n_pixreco_expected:
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
        elapsed = time.time() - self.scan_start
        prior_processing_secs = self.scan_start - self.global_start_time
        proc_stats = {
            "start": {
                'entire scan': str(
                    dt.datetime.fromtimestamp(int(self.global_start_time))
                ),
                # TODO: add a start time for each nside (async), or just "scan_start"
                'this iteration': str(dt.datetime.fromtimestamp(int(self.scan_start))),
            },
            "runtime": {
                'prior processing': str(
                    dt.timedelta(seconds=int(prior_processing_secs))
                ),
                # TODO: remove 'iterations' -- no replacement b/c async, that's OK
                'this iteration': str(dt.timedelta(seconds=int(elapsed))),
                'this iteration + prior processing': str(
                    dt.timedelta(seconds=int(elapsed + prior_processing_secs))
                ),
                'total': str(
                    dt.timedelta(seconds=int(time.time() - self.global_start_time))
                ),
            },
        }
        if not self.pixreco_ct:  # we can't predict
            return proc_stats

        secs_per_pixreco = elapsed / self.pixreco_ct
        proc_stats['rate'] = {
            'average reco (scanner wall time)': str(
                dt.timedelta(seconds=int(secs_per_pixreco))
            ),
            'average reco (worker time)': str(
                dt.timedelta(seconds=int(self.worker_rates.average))
            ),
            'slowest reco (worker time)': str(
                dt.timedelta(seconds=int(self.worker_rates.slowest))
            ),
            'fastest reco (worker time)': str(
                dt.timedelta(seconds=int(self.worker_rates.fastest))
            ),
        }

        if self.is_event_scan_done:
            # SCAN IS DONE
            proc_stats['end'] = str(dt.datetime.fromtimestamp(int(time.time())))
            proc_stats['finished'] = True
        else:
            # MAKE PREDICTIONS
            # NOTE: this is a simple average, may want to visit more sophisticated methods
            secs_predicted = elapsed / (self.pixreco_ct / self.n_pixreco_expected)
            proc_stats['predictions'] = {
                # TODO:
                # 'remaining': {
                #     # counts are downplayed using 'amount remaining' so we never report percent done
                #     'percent': ##,
                #     'pixels': ###/###,
                #     'recos': ####/####,
                # },
                'time left': {
                    # TODO: replace w/ 'entire scan'
                    'this iteration': str(
                        dt.timedelta(seconds=int(secs_predicted - elapsed))
                    )
                },
                'total runtime at finish': {
                    # TODO: replace w/ 'total reconstruction'
                    'this iteration': str(dt.timedelta(seconds=int(secs_predicted))),
                    # TODO: replace w/ 'entire scan'
                    'this iteration + prior processing': str(
                        dt.timedelta(
                            seconds=int(secs_predicted + prior_processing_secs)
                        )
                    ),
                },
            }

        return proc_stats

    def _get_tallies(self) -> StrDict:
        """Get a multi-dict progress report of the nsides_dict's contents."""
        saved = {}
        if self.nsides_dict:
            for nside in sorted(self.nsides_dict):  # sorted by nside
                saved[nside] = len(self.nsides_dict[nside])

        # TODO: remove for #84
        this_iteration = {}  # type: ignore[var-annotated]
        if self._n_pixreco_expected is not None:
            this_iteration = {
                'percent': (self.pixreco_ct / self.n_pixreco_expected) * 100,
                'pixels': f"{self.pixreco_ct/self.n_posvar}/{self.n_pixreco_expected/self.n_posvar}",
                'recos': f"{self.pixreco_ct}/{self.n_pixreco_expected}",
            }

        return {
            'by_nside': saved,
            'total': sum(s for s in saved.values()),  # total completed pixels
            # TODO: for #84: uncomment b/c this will now be scan-wide total & remove 'this iteration' dict
            # 'total_recos': self.pixreco_ct,
            'this_iteration': this_iteration,  # TODO: remove for #84
        }

    async def final_computing_report(self) -> None:
        """Check if all the pixel-recos were received & make a final report."""
        self._check_call_order(self.final_computing_report)
        if not self.pixreco_ct:
            raise RuntimeError("No pixel-reconstructions were ever received.")

        if self.pixreco_ct != self.n_pixreco_expected:
            raise RuntimeError(
                f"Not all pixel-reconstructions were received: "
                f"{self.pixreco_ct}/{self.n_pixreco_expected} ({self.pixreco_ct/self.n_pixreco_expected})"
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
        epilogue_msg: str = '',
        total_n_pixreco_expected: int = None,  # TODO: remove for https://github.com/icecube/skymap_scanner/issues/84
    ) -> None:
        """Send progress to SkyDriver (if the connection is established)."""
        progress = {
            'summary': summary_msg,
            'epilogue': epilogue_msg,
            'tallies': self._get_tallies(),
            'processing_stats': self._get_processing_progress(),
        }
        scan_metadata = {
            'scan_id': self.scan_id,
            'min_nside': self.min_nside,  # TODO: replace with nsides (https://github.com/icecube/skymap_scanner/issues/79)
            'max_nside': self.max_nside,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
            'position_variations': self.n_posvar,
        }

        if total_n_pixreco_expected:
            # TODO: remove for https://github.com/icecube/skymap_scanner/issues/84
            # see _get_tallies()
            progress['tallies']['total_recos'] = total_n_pixreco_expected

        LOGGER.info(pyobj_to_string_repr(progress))
        if not self.skydriver_rc:
            return

        body = {
            'progress': progress,
            'event_metadata': dc.asdict(self.event_metadata),
            'scan_metadata': scan_metadata,
        }
        await self.skydriver_rc.request("PATCH", f"/scan/manifest/{self.scan_id}", body)

    async def _send_result(self) -> ScanResult:
        """Send result to SkyDriver (if the connection is established)."""
        result = self._get_result()
        serialized = result.serialize()

        LOGGER.info(pyobj_to_string_repr(serialized))
        if not self.skydriver_rc:
            return result

        body = {'skyscan_result': serialized, 'is_final': self.is_event_scan_done}
        await self.skydriver_rc.request("PUT", f"/scan/result/{self.scan_id}", body)

        return result
