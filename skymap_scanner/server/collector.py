"""The Skymap Scanner Server."""


import dataclasses as dc
import itertools
import time
from bisect import bisect
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy
from icecube import icetray  # type: ignore[import]  # pylint: disable=import-error

from .. import config as cfg
from ..utils.pixelreco import NSidesDict, PixelReco, PixelRecoID
from . import LOGGER
from .reporter import Reporter

StrDict = Dict[str, Any]


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class SentPixelVariation:
    """Used for tracking a single sent pixel variation."""

    nside: int
    pixel_id: int
    posvar_id: int
    sent_time: float = dc.field(compare=False)  # compare also excludes field from hash

    @staticmethod
    def from_pframe(pframe: icetray.I3Frame) -> "SentPixelVariation":
        """Get an instance from a Pframe."""
        return SentPixelVariation(
            nside=pframe[cfg.I3FRAME_NSIDE].value,
            pixel_id=pframe[cfg.I3FRAME_PIXEL].value,
            posvar_id=pframe[cfg.I3FRAME_POSVAR].value,
            sent_time=time.time(),
        )

    def matches_pixreco(self, pixreco: PixelReco) -> bool:
        """Does this match the PixelReco instance?"""
        return (
            self.nside == pixreco.nside
            and self.pixel_id == pixreco.pixel
            and self.posvar_id == pixreco.pos_var_index
        )


class ExtraPixelRecoException(Exception):
    """Raised when a pixel-reco (message) is received that is semantically
    equivalent to a prior.

    For example, a pixel-reco (message) that has the same NSide, Pixel
    ID, and Variation ID as an already received message.
    """


class BestPixelRecoFinder:
    """Facilitate finding the best reco result for any pixel."""

    def __init__(
        self,
        n_posvar: int,  # Number of position variations to collect
    ) -> None:
        if n_posvar <= 0:
            raise ValueError(f"n_posvar is not positive: {n_posvar}")
        self.n_posvar = n_posvar

        self.pixelNumToFramesMap: Dict[
            Tuple[icetray.I3Int, icetray.I3Int], List[PixelReco]
        ] = {}

    def cache_and_get_best(self, pixreco: PixelReco) -> Optional[PixelReco]:
        """Add pixreco to internal cache and possibly return the best reco for
        pixel.

        If all the recos for the embedded pixel have be received, return
        the best one. Otherwise, return None.
        """
        index = (pixreco.nside, pixreco.pixel)

        if index not in self.pixelNumToFramesMap:
            self.pixelNumToFramesMap[index] = []
        self.pixelNumToFramesMap[index].append(pixreco)

        if len(self.pixelNumToFramesMap[index]) >= self.n_posvar:
            # find minimum llh
            best = None
            for this in self.pixelNumToFramesMap[index]:
                if (not best) or (this.llh < best.llh and not numpy.isnan(this.llh)):
                    best = this
            if best is None:
                # just push the first if all of them are nan
                best = self.pixelNumToFramesMap[index][0]

            del self.pixelNumToFramesMap[index]  # del list
            return best

        return None

    def finish(self) -> None:
        """Check if all the pixel-recos were received.

        If an entire pixel (and all its pixel-recos) was dropped by
        client(s), this will not catch it.
        """
        if len(self.pixelNumToFramesMap) != 0:
            raise RuntimeError(
                f"Pixels left in cache, not all of the packets seem to be complete: "
                f"{self.pixelNumToFramesMap}"
            )


class PixelRecoCollector:
    """Manage the collecting, filtering, reporting, and saving of pixel-reco
    results."""

    def __init__(
        self,
        n_posvar: int,  # Number of position variations to collect
        nsides_dict: NSidesDict,
        reporter: Reporter,
        predictive_scanning_threshold: float,
        nsides: List[int],
    ) -> None:
        self._finder = BestPixelRecoFinder(n_posvar=n_posvar)
        self._in_finder_context = False

        self.reporter = reporter

        # data stores
        self.nsides_dict = nsides_dict
        self._pixrecoid_received_quick_lookup: Set[PixelRecoID] = set([])
        self._sent_pixvars_by_nside: Dict[int, List[SentPixelVariation]] = {}

        # percentage progress trackers
        self._thresholds = PixelRecoCollector._make_thresholds(
            predictive_scanning_threshold
        )
        self._nsides_percents_done = {n: 0.0 for n in nsides}

    @staticmethod
    def _make_thresholds(predictive_scanning_threshold: float) -> List[float]:
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

        thresholds = [predictive_scanning_threshold]
        base = sorted([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        thresholds.extend(base[bisect(base, predictive_scanning_threshold) :])

        LOGGER.info(f"Thresholds: {thresholds}")
        return thresholds

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
        def __init__(self, finder: BestPixelRecoFinder, parent: "PixelRecoCollector"):
            self.finder = finder
            self.parent = parent

        async def __aenter__(self) -> "PixelRecoCollector._FinderContextManager":
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
                self.reporter.increment_pixels_sent_ct(spv.nside)
                try:
                    self._sent_pixvars_by_nside[spv.nside].append(spv)
                except KeyError:
                    self._sent_pixvars_by_nside[spv.nside] = [spv]

            await self.reporter.make_reports_if_needed(
                bypass_timers=True,
                summary_msg="The Skymap Scanner has sent out pixels and is waiting to receive recos.",
            )
        else:
            await self.reporter.make_reports_if_needed(
                bypass_timers=True,
                summary_msg="The Skymap Scanner is waiting to receive recos.",
            )

    async def collect(
        self,
        pixreco: PixelReco,
        pixreco_runtime: float,
    ) -> None:
        """Cache pixreco until we can save the pixel's best received reco."""
        if not self._in_finder_context:
            raise RuntimeError(
                "Must be in `PixelRecoCollector.finder_context()` context."
            )
        LOGGER.debug(f"{self.nsides_dict=}")

        if pixreco.id_tuple in self._pixrecoid_received_quick_lookup:
            raise ExtraPixelRecoException(
                f"Pixel-reco has already been received: {pixreco.id_tuple}"
            )

        # match to corresponding SentPixelVariation
        sent_pixvar = None
        for sent_pixvar in self._sent_pixvars_by_nside[pixreco.nside]:
            if sent_pixvar.matches_pixreco(pixreco):
                break
        if not sent_pixvar:
            raise ExtraPixelRecoException(
                f"Pixel-reco received not in sent set: {pixreco.id_tuple}"
            )

        # append
        self._pixrecoid_received_quick_lookup.add(pixreco.id_tuple)
        logging_id = f"S#{len(self._pixrecoid_received_quick_lookup) - 1}"
        LOGGER.info(f"Got a pixel-reco {logging_id} {pixreco}")

        # get best pixreco
        best = self._finder.cache_and_get_best(pixreco)
        LOGGER.info(f"Cached pixel-reco {pixreco.id_tuple} {pixreco}")

        # save best pixreco (if we got it)
        if not best:
            LOGGER.debug(f"Best pixel-reco not yet found ({pixreco.id_tuple} {pixreco}")
        else:
            LOGGER.info(
                f"Saving a BEST pixel-reco (found {logging_id}): "
                f"{best.id_tuple} {best}"
            )
            # insert pixreco into nsides_dict
            if best.nside not in self.nsides_dict:
                self.nsides_dict[best.nside] = {}
            if best.pixel in self.nsides_dict[best.nside]:
                raise ExtraPixelRecoException(
                    f"NSide {best.nside} / Pixel {best.pixel} is already in nsides_dict"
                )
            self.nsides_dict[best.nside][best.pixel] = best
            LOGGER.debug(f"Saved (found during {logging_id}): {best.id_tuple} {best}")

        # report after potential save
        await self.reporter.record_pixreco(
            pixreco.nside,
            pixreco_runtime,
            roundtrip_start=sent_pixvar.sent_time,
            roundtrip_end=time.time(),
        )

    def collected_everything_sent(self) -> bool:
        """Has every pixel been collected?"""
        # first check lengths, faster: O(1)
        if self.n_sent != len(self._pixrecoid_received_quick_lookup):
            return False
        # now, sanity check contents, slower: O(n)
        sent_ids = set((p.nside, p.pixel_id, p.posvar_id) for p in self.sent_pixvars)
        if sent_ids == self._pixrecoid_received_quick_lookup:
            return True
        raise RuntimeError(
            f"Sanity check failed: Collected enough pixels,"
            f" but does not match: {sent_ids=} vs {self._pixrecoid_received_quick_lookup=}"
        )

    def get_max_nside_to_refine(self) -> Optional[int]:
        """Return max nside value from all nsides that just now breached a new
        threshold.

        Return `None` if no nsides just now breached a new threshold
        """
        if not self.nsides_dict:  # nothing has been saved yet
            return None

        # recalculate nsides' percentage done
        updated_percents = {}
        for nside, spv in self._sent_pixvars_by_nside.items():
            finished = len(self.nsides_dict[nside]) * self._finder.n_posvar
            updated_percents[nside] = finished / len(spv)

        def bin_it(percent: float) -> float:
            return self._thresholds[bisect(self._thresholds, percent) - 1]

        def reached_new_threshold(nside: int, percent: float) -> bool:
            if percent < self._thresholds[0]:  # doesn't meet minimum threshold
                return False
            # did percentage reached new threshold?
            if nside not in self._nsides_percents_done:
                old_bin = 0.0
            else:
                old_bin = bin_it(self._nsides_percents_done[nside])
            return bin_it(percent) > old_bin

        newly_thresholded_nsides = [
            nside
            for nside, prog in updated_percents.items()
            if reached_new_threshold(nside, prog)
        ]
        self._nsides_percents_done = updated_percents

        if not newly_thresholded_nsides:
            return None
        return max(newly_thresholded_nsides)
