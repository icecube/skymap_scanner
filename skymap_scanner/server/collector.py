"""The Skymap Scanner Server."""

import itertools
import logging
import time
from bisect import bisect
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy

from .reporter import Reporter
from .. import config as cfg
from ..utils.pixel_classes import (
    NSidesDict,
    PTuple,
    RecoPixelFinal,
    RecoPixelVariation,
    SentPixelVariation,
)

LOGGER = logging.getLogger(__name__)


StrDict = Dict[str, Any]


class ExtraRecoPixelVariationException(Exception):
    """Raised when a RecoPixelVariation (message) is received that is
    semantically equivalent to a prior.

    For example, a RecoPixelVariation (message) that has the same NSide,
    Pixel ID, and Variation ID as an already received message.
    """


class RecoPixelFinalFinder:
    """Facilitate finding the best reco result for any pixel variation."""

    def __init__(
        self,
        n_posvar: int,  # Number of position variations to collect
    ) -> None:
        if n_posvar <= 0:
            raise ValueError(f"n_posvar is not positive: {n_posvar}")
        self.n_posvar = n_posvar

        self.cache_by_nside_pixid: Dict[Tuple[int, int], List[RecoPixelVariation]] = {}

    def cache_and_get_best(
        self, reco_pixel_variation: RecoPixelVariation
    ) -> Optional[RecoPixelFinal]:
        """Add pixfin to internal cache and possibly return the best reco for
        pixel.

        If all the recos for the embedded pixel have be received, return
        the best one. Otherwise, return None.
        """
        index = (reco_pixel_variation.nside, reco_pixel_variation.pixel_id)

        if index not in self.cache_by_nside_pixid:
            self.cache_by_nside_pixid[index] = []
        self.cache_by_nside_pixid[index].append(reco_pixel_variation)

        if len(self.cache_by_nside_pixid[index]) >= self.n_posvar:
            # find minimum llh
            best = None
            for this in self.cache_by_nside_pixid[index]:
                if (not best) or (this.llh < best.llh and not numpy.isnan(this.llh)):
                    best = this
            if best is None:
                # just push the first if all of them are nan
                best = self.cache_by_nside_pixid[index][0]

            del self.cache_by_nside_pixid[index]  # del list
            return RecoPixelFinal.from_recopixelvariation(best)

        return None

    def finish(self) -> None:
        """Check if all the RecoPixelFinal were received/retrieved.

        If an entire pixel (and all its variations) was dropped by
        client(s), this will not catch it.
        """
        if len(self.cache_by_nside_pixid) != 0:
            raise RuntimeError(
                f"Pixels left in cache, not all of the packets seem to be complete: "
                f"{self.cache_by_nside_pixid}"
            )


class Collector:
    """Manage collecting, filtering, reporting, and saving of
    RecoPixelFinals."""

    def __init__(
        self,
        n_posvar: int,  # Number of position variations to collect
        nsides_dict: NSidesDict,
        reporter: Reporter,
        predictive_scanning_threshold: float,
        nsides: List[int],
    ) -> None:
        self._finder = RecoPixelFinalFinder(n_posvar=n_posvar)
        self._in_finder_context = False

        self.reporter = reporter

        # data stores
        self.nsides_dict = nsides_dict
        self._pixfinid_received_quick_lookup: Set[PTuple] = set([])
        self._sent_pixvars_by_nside: Dict[int, List[SentPixelVariation]] = {}

        # percentage progress trackers
        self._nsides_thresholds = Collector._make_nsides_thresholds(
            predictive_scanning_threshold, nsides
        )
        self._nsides_percents_done = {n: 0.0 for n in nsides}

    @staticmethod
    def _make_nsides_thresholds(
        predictive_scanning_threshold: float, nsides: List[int]
    ) -> Dict[int, List[float]]:
        """Ex: predictive_scanning_threshold=0.66 -> [0.66, .7, 0.8, 0.9, 1.0]."""
        if not (
            cfg.PREDICTIVE_SCANNING_THRESHOLD_MIN
            < predictive_scanning_threshold
            <= cfg.PREDICTIVE_SCANNING_THRESHOLD_MAX
        ):
            raise ValueError(
                f"`predictive_scanning_threshold` must be "
                f"[{cfg.PREDICTIVE_SCANNING_THRESHOLD_MIN}, "
                f"{cfg.PREDICTIVE_SCANNING_THRESHOLD_MAX}]: "
                f"'{predictive_scanning_threshold}'"
            )

        # make standard threshold series
        base_thresholds = sorted(set(cfg.COLLECTOR_BASE_THRESHOLDS + [1.0]))
        thresholds = [predictive_scanning_threshold]
        bstart = bisect(base_thresholds, predictive_scanning_threshold)
        thresholds.extend(base_thresholds[bstart:])
        if (
            min(thresholds) < cfg.PREDICTIVE_SCANNING_THRESHOLD_MIN
            or max(thresholds) > cfg.PREDICTIVE_SCANNING_THRESHOLD_MAX
        ):
            raise ValueError(
                f"Each threshold series must be "
                f"[{cfg.PREDICTIVE_SCANNING_THRESHOLD_MIN}, "
                f"{cfg.PREDICTIVE_SCANNING_THRESHOLD_MAX}]: "
                f"'{thresholds}'"
            )

        # make threshold series for each nside
        by_nsides = {n: thresholds for n in nsides}
        by_nsides[max(nsides)] = [1.0]  # final nside must reach 100%
        LOGGER.info(f"Thresholds: {by_nsides}")
        if not all(t[-1] == 1.0 for t in by_nsides.values()):
            raise ValueError(f"Each threshold series must end with 1.0: {by_nsides}")

        return by_nsides

    @property
    def n_sent(self) -> int:
        return sum(len(x) for x in self._sent_pixvars_by_nside.values())

    @property
    def sent_pixvars(self) -> Set[SentPixelVariation]:
        """Just the PixelSent instances that have been sent."""
        return set(itertools.chain(*self._sent_pixvars_by_nside.values()))

    def finder_context(self) -> "_FinderContextManager":
        """Creates a context manager for startup & ending conditions."""
        return self._FinderContextManager(self._finder, self)

    class _FinderContextManager:
        def __init__(self, finder: RecoPixelFinalFinder, parent: "Collector"):
            self.finder = finder
            self.parent = parent

        async def __aenter__(self) -> "Collector._FinderContextManager":
            self.parent._in_finder_context = True
            return self

        async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:  # type: ignore[no-untyped-def]
            self.finder.finish()
            self.parent._in_finder_context = False

    async def register_sent_pixvars(
        self, addl_sent_pixvars: Set[SentPixelVariation]
    ) -> None:
        """Register the pixel ids recently sent.

        When `addl_sent_pixvars` is empty (happens at the end of the
        scan), `self.predictive_scanning_threshold` will now be ignored.
        """
        if addl_sent_pixvars:
            for spv in addl_sent_pixvars:
                self.reporter.increment_sent_ct(spv.nside)
                try:
                    self._sent_pixvars_by_nside[spv.nside].append(spv)
                except KeyError:
                    self._sent_pixvars_by_nside[spv.nside] = [spv]

            await self.reporter.make_reports_if_needed(
                bypass_timers=True,
                summary_msg=(
                    f"The Skymap Scanner has sent out {len(addl_sent_pixvars)} "
                    f"pixels and is waiting to receive recos."
                ),
            )
        else:
            await self.reporter.make_reports_if_needed(
                bypass_timers=True,
                summary_msg="The Skymap Scanner is waiting to receive recos.",
            )

    async def collect(
        self,
        reco_pixel_variation: RecoPixelVariation,
        on_worker_runtime: float,
    ) -> None:
        """Cache RecoPixelVariation until we can save the pixel's best received
        reco (RecoPixelFinal)."""
        if not self._in_finder_context:
            raise RuntimeError("Must be in `Collector.finder_context()` context.")
        LOGGER.debug(  # don't log HUGE string
            f"self.nsides_dict info (# pixels per nside): {[(k,len(v)) for k, v in self.nsides_dict.items()]}"
        )

        if reco_pixel_variation.id_tuple in self._pixfinid_received_quick_lookup:
            raise ExtraRecoPixelVariationException(
                f"RecoPixelVariation has already been received: {reco_pixel_variation.id_tuple}"
            )

        # match to corresponding SentPixelVariation
        sent_pixvar = None
        for sent_pixvar in self._sent_pixvars_by_nside[reco_pixel_variation.nside]:
            if sent_pixvar.matches_reco_pixel_variation(reco_pixel_variation):
                break
        if not sent_pixvar:
            raise ExtraRecoPixelVariationException(
                f"RecoPixelVariation received not in sent set: {reco_pixel_variation.id_tuple}"
            )

        # append
        self._pixfinid_received_quick_lookup.add(reco_pixel_variation.id_tuple)
        logging_id = f"S#{len(self._pixfinid_received_quick_lookup) - 1}"
        LOGGER.info(
            f"Got RecoPixelVariation {logging_id} {reco_pixel_variation.id_tuple}"
        )

        # get best pixfin
        pixfin = self._finder.cache_and_get_best(reco_pixel_variation)
        LOGGER.debug(f"Cached RecoPixelVariation {reco_pixel_variation.id_tuple}")

        # save pixfin (if we got it)
        if not pixfin:
            LOGGER.debug(
                f"RecoPixelFinal not yet done ({reco_pixel_variation.id_tuple} {reco_pixel_variation}"
            )
        else:
            LOGGER.info(
                f"Saving RecoPixelFinal (done @ {logging_id}): {(pixfin.nside,pixfin.pixel_id)}"
            )
            # insert pixfin into nsides_dict
            if pixfin.nside not in self.nsides_dict:
                self.nsides_dict[pixfin.nside] = {}
            if pixfin.pixel_id in self.nsides_dict[pixfin.nside]:
                raise ExtraRecoPixelVariationException(
                    f"NSide {pixfin.nside} / Pixel {pixfin.pixel_id} is already in nsides_dict"
                )
            self.nsides_dict[pixfin.nside][pixfin.pixel_id] = pixfin
            LOGGER.debug(f"Saved (found during {logging_id}): {pixfin}")

        # report after potential save
        await self.reporter.record_reco(
            reco_pixel_variation.nside,
            on_worker_runtime,
            on_server_roundtrip_start=sent_pixvar.sent_time,
            on_server_roundtrip_end=time.time(),
        )

    def has_collected_all_sent(self) -> bool:
        """Has every pixel been collected?"""
        # first check lengths, faster: O(1)
        if self.n_sent != len(self._pixfinid_received_quick_lookup):
            return False
        # now, sanity check contents, slower: O(n)
        sent_ids = set((p.nside, p.pixel_id, p.posvar_id) for p in self.sent_pixvars)
        if sent_ids == self._pixfinid_received_quick_lookup:
            LOGGER.info("Collected all sent")
            return True
        raise RuntimeError(
            f"Sanity check failed: Collected enough pixels,"
            f" but does not match: {sent_ids=} vs {self._pixfinid_received_quick_lookup=}"
        )

    def get_max_nside_thresholded(self) -> Optional[int]:
        """Return max nside value from all nsides that just now breached a new
        threshold.

        Return `None` if no nsides just now breached a new threshold
        """
        if not self.nsides_dict:  # nothing has been saved yet
            return None

        # recalculate nsides' percentage done
        updated_percents = {}
        for nside, spv in self._sent_pixvars_by_nside.items():
            finished = len(self.nsides_dict.get(nside, [])) * self._finder.n_posvar
            updated_percents[nside] = finished / len(spv)

        def bin_it(nside: int, percent: float) -> float:
            # find the threshold bin (floor) for the nside (0.0 if too low)
            prev_bin = 0.0
            for tbin in self._nsides_thresholds[nside]:
                if percent < tbin:
                    return prev_bin
                prev_bin = tbin
            return self._nsides_thresholds[nside][-1]  # it's the last bin

        def reached_new_threshold(nside: int, percent: float) -> bool:
            # did percentage reached new threshold?
            old_bin = bin_it(nside, self._nsides_percents_done.get(nside, 0.0))
            return bin_it(nside, percent) > old_bin

        newly_thresholded_nsides = [
            nside
            for nside, percent in updated_percents.items()
            if reached_new_threshold(nside, percent)
        ]
        LOGGER.debug(f"Old percents done: {self._nsides_percents_done}")
        LOGGER.debug(f"New percents done: {updated_percents}")
        LOGGER.debug(f"Newly thresholded nsides: {newly_thresholded_nsides}")
        self._nsides_percents_done = updated_percents

        if not newly_thresholded_nsides:
            return None
        LOGGER.info(
            f"Met thresholds: {newly_thresholded_nsides} ({self._nsides_percents_done})"
        )
        return max(newly_thresholded_nsides)
