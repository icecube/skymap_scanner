"""The Skymap Scanner Server."""

# pylint: disable=invalid-name,import-error
# fmt:quotes-ok

import argparse
import asyncio
import dataclasses as dc
import itertools
import json
import logging
import math
import random
import time
from bisect import bisect
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import healpy  # type: ignore[import]
import mqclient as mq
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]
    astro,
    dataclasses,
    full_event_followup,
    icetray,
)
from rest_tools.client import RestClient
from wipac_dev_tools import argparse_tools, logging_tools

from .. import config as cfg
from .. import recos
from ..utils import extract_json_message
from ..utils.event_tools import EventMetadata
from ..utils.load_scan_state import get_baseline_gcd_frames
from ..utils.pixelreco import NSidesDict, PixelReco, PixelRecoID, pframe_to_pixelrecoid
from . import LOGGER
from .pixels import choose_pixels_to_reconstruct
from .reporter import Reporter
from .utils import NSideProgression, fetch_event_contents

StrDict = Dict[str, Any]


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class SentPixel:
    """Used for tracking a single sent pixel."""

    nside: int
    pixel_id: int
    posvar_id: int
    sent_time: float = dc.field(compare=False)  # compare also excludes field from hash

    @staticmethod
    def from_pframe(pframe: icetray.I3Frame) -> 'SentPixel':
        """Get an instance from a Pframe."""
        return SentPixel(
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


# fmt: off
class PixelsToReco:
    """Manage providing pixels to reco."""

    def __init__(
        self,
        nsides_dict: NSidesDict,
        GCDQp_packet: List[icetray.I3Frame],
        baseline_GCD: str,
        min_nside: int,
        input_time_name: str,
        input_pos_name: str,
        output_particle_name: str,
        reco_algo: str,
        event_metadata: EventMetadata,
    ) -> None:
        """
        Arguments:
            `nsides_dict`
                - the nsides_dict
            `GCDQp_packet`
                - the GCDQp frame packet
            `min_nside`
                - the minimum nside value
            `input_time_name`
                - name of an I3Double to use as the vertex time for the coarsest scan
            `input_pos_name`
                - name of an I3Position to use as the vertex position for the coarsest scan
            `output_particle_name`
                - name of the output I3Particle
            `reco_algo`
                - name of the reconstruction algorithm to run
            `event_metadata`
                - a collection of metadata about the event
        """
        self.nsides_dict = nsides_dict
        self.input_pos_name = input_pos_name
        self.input_time_name = input_time_name
        self.output_particle_name = output_particle_name
        self.reco_algo = reco_algo.lower()

        # Get Position Variations
        variation_distance = 20.*I3Units.m
        if self.reco_algo == 'millipede_original':
            if cfg.ENV.SKYSCAN_MINI_TEST:
                self.pos_variations = [
                    dataclasses.I3Position(0.,0.,0.),
                    dataclasses.I3Position(-variation_distance,0.,0.)
                ]
            else:
                self.pos_variations = [
                    dataclasses.I3Position(0.,0.,0.),
                    dataclasses.I3Position(-variation_distance,0.,0.),
                    dataclasses.I3Position(variation_distance,0.,0.),
                    dataclasses.I3Position(0.,-variation_distance,0.),
                    dataclasses.I3Position(0., variation_distance,0.),
                    dataclasses.I3Position(0.,0.,-variation_distance),
                    dataclasses.I3Position(0.,0., variation_distance)
                ]
        else:
            self.pos_variations = [
                dataclasses.I3Position(0.,0.,0.),
            ]

        # Set min nside
        self.min_nside = min_nside

        # Validate & read GCDQp_packet
        p_frame = GCDQp_packet[-1]
        g_frame = get_baseline_gcd_frames(baseline_GCD, GCDQp_packet)[0]

        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.fallback_position = p_frame[self.input_pos_name]
        self.fallback_time = p_frame[self.input_time_name].value
        self.fallback_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_metadata = event_metadata
        if self.event_metadata.run_id != self.event_header.run_id or self.event_metadata.event_id != self.event_header.event_id:
            raise Exception(
                f"Run/Event Mismatch: {self.event_metadata} vs "
                f"({self.event_header.run_id=}, {self.event_header.event_id=})"
            )

        self.pulseseries_hlc = dataclasses.I3RecoPulseSeriesMap.from_frame(p_frame,'SplitUncleanedInIcePulsesHLC')
        self.omgeo = g_frame["I3Geometry"].omgeo

    @staticmethod
    def refine_vertex_time(vertex, time, direction, pulses, omgeo):
        thc = dataclasses.I3Constants.theta_cherenkov
        ccc = dataclasses.I3Constants.c
        min_d = numpy.inf
        min_t = time
        adj_d = 0
        for om in pulses.keys():
            rvec = omgeo[om].position-vertex
            _l = -rvec*direction
            _d = numpy.sqrt(rvec.mag2-_l**2) # closest approach distance
            if _d < min_d: # closest om
                min_d = _d
                min_t = pulses[om][0].time
                adj_d = _l+_d/numpy.tan(thc)-_d/(numpy.cos(thc)*numpy.sin(thc)) # translation distance
        if numpy.isinf(min_d):
            return time
        return min_t + adj_d/ccc

    def gen_new_pixel_pframes(
        self,
        already_sent_pixels: Set[SentPixel],
        nside_subprogression: NSideProgression,
    ) -> Iterator[icetray.I3Frame]:
        """Yield pixels (PFrames) to be reco'd for each `nside_available`."""

        def pixel_already_sent(pixel: Tuple[icetray.I3Int, icetray.I3Int]) -> bool:
            # Has this pixel already been sent? Ignore the position-variation id
            for sent_pixel in already_sent_pixels:
                if sent_pixel.nside == pixel[0] and sent_pixel.pixel_id == pixel[1]:
                    return True
            return False

        # find pixels to refine
        pixels_to_refine = choose_pixels_to_reconstruct(self.nsides_dict, nside_subprogression)
        pixels_to_refine = set(p for p in pixels_to_refine if not pixel_already_sent(p))
        if not pixels_to_refine:
            LOGGER.info("There are no pixels to refine.")
            return
        LOGGER.debug(f"Got pixels to refine: {pixels_to_refine}")

        # submit the pixels we need to submit (in random order)
        for i, (nside, pix) in enumerate(sorted(pixels_to_refine, key=lambda _: random.random())):
            LOGGER.debug(f"Generating pframe(s) from pixel P#{i}: {(nside, pix)}")
            yield from self._gen_pframes(nside=nside, pixel=pix)

    def i3particle(self, position, direction, energy, time):
        # generate the particle from scratch
        particle = dataclasses.I3Particle()
        particle.shape = dataclasses.I3Particle.ParticleShape.InfiniteTrack
        particle.fit_status = dataclasses.I3Particle.FitStatus.OK
        particle.pos = position
        particle.dir = direction
        if self.reco_algo == 'millipede_original':
            LOGGER.debug(f"Reco_algo is {self.reco_algo}, not refining time")
            particle.time = time
        else:
            LOGGER.debug(f"Reco_algo is {self.reco_algo}, refining time")
            # given direction and vertex position, calculate time from CAD
            particle.time = self.refine_vertex_time(
                position,
                time,
                direction,
                self.pulseseries_hlc,
                self.omgeo)
        particle.energy = energy
        return particle

    def _gen_pframes(
        self,
        nside: icetray.I3Int,
        pixel: icetray.I3Int,
    ) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be reco'd for a given `nside` and `pixel`."""

        dec, ra = healpy.pix2ang(nside, pixel)
        dec = dec - numpy.pi/2.
        zenith, azimuth = astro.equa_to_dir(ra, dec, self.event_metadata.mjd)
        zenith = float(zenith)
        azimuth = float(azimuth)
        direction = dataclasses.I3Direction(zenith,azimuth)

        if nside == self.min_nside:
            position = self.fallback_position
            time = self.fallback_time
            energy = self.fallback_energy
        else:
            coarser_nside = nside
            while True:
                coarser_nside = coarser_nside/2
                coarser_pixel = healpy.ang2pix(int(coarser_nside), dec+numpy.pi/2., ra)

                if coarser_nside < self.min_nside:
                    break # no coarser pixel is available (probably we are just scanning finely around MC truth)
                    #raise RuntimeError("internal error. cannot find an original coarser pixel for nside={0}/pixel={1}".format(nside, pixel))

                if coarser_nside in self.nsides_dict:
                    if coarser_pixel in self.nsides_dict[coarser_nside]:
                        # coarser pixel found
                        break

            if coarser_nside < self.min_nside:
                # no coarser pixel is available (probably we are just scanning finely around MC truth)
                position = self.fallback_position
                time = self.fallback_time
                energy = self.fallback_energy
            else:
                if numpy.isnan(self.nsides_dict[coarser_nside][coarser_pixel].llh):
                    # coarser reconstruction failed
                    position = self.fallback_position
                    time = self.fallback_time
                    energy = self.fallback_energy
                else:
                    position = self.nsides_dict[coarser_nside][coarser_pixel].position
                    time = self.nsides_dict[coarser_nside][coarser_pixel].time
                    energy = self.nsides_dict[coarser_nside][coarser_pixel].energy

        for i in range(0,len(self.pos_variations)):
            p_frame = icetray.I3Frame(icetray.I3Frame.Physics)
            posVariation = self.pos_variations[i]

            if self.reco_algo == 'millipede_wilks':
                # rotate variation to be applied in transverse plane
                posVariation.rotate_y(direction.theta)
                posVariation.rotate_z(direction.phi)
                if position != self.fallback_position:
                    # add fallback pos as an extra first guess
                    p_frame[f'{self.output_particle_name}_fallback'] = self.i3particle(
                        self.fallback_position+posVariation,
                        direction,
                        self.fallback_energy,
                        self.fallback_time)

            p_frame[f'{self.output_particle_name}'] = self.i3particle(position+posVariation,
                                                                      direction,
                                                                      energy,
                                                                      time)
            # generate a new event header
            eventHeader = dataclasses.I3EventHeader(self.event_header)
            eventHeader.sub_event_stream = "SCAN_nside%04u_pixel%04u_posvar%04u" % (nside, pixel, i)
            eventHeader.sub_event_id = int(pixel)
            p_frame["I3EventHeader"] = eventHeader
            p_frame[cfg.I3FRAME_PIXEL] = icetray.I3Int(int(pixel))
            p_frame[cfg.I3FRAME_NSIDE] = icetray.I3Int(int(nside))
            p_frame[cfg.I3FRAME_POSVAR] = icetray.I3Int(int(i))

            LOGGER.debug(
                f"Yielding PFrame (pixel position-variation) PV#{i} "
                f"({pframe_to_pixelrecoid(p_frame)}) ({posVariation=})..."
            )
            yield p_frame


# fmt: on
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
        self._sent_pixels_by_nside: Dict[int, List[SentPixel]] = {}

        # percentage progress trackers
        self._thresholds = PixelRecoCollector._make_thresholds(
            predictive_scanning_threshold
        )
        self._nsides_percents_done = {n: 0.0 for n in nsides}

    @staticmethod
    def _make_thresholds(predictive_scanning_threshold: float) -> List[float]:
        """Ex: predictive_scanning_threshold=0.66 -> [0.66, .7, 0.8, 0.9, 1.0]."""
        if not (0.0 < predictive_scanning_threshold <= 1.0):
            raise ValueError("`predictive_scanning_threshold` must be (0.0, 1.0])")

        thresholds = [predictive_scanning_threshold]
        base = sorted([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        thresholds.extend(base[bisect(base, predictive_scanning_threshold) :])

        LOGGER.info(f"Thresholds: {thresholds}")
        return thresholds

    @property
    def n_sent(self) -> int:
        return sum(len(x) for x in self._sent_pixels_by_nside.values())

    @property
    def sent_pixels(self) -> Set[SentPixel]:
        """Just the PixelSent instances that have been sent."""
        return set(itertools.chain(*self._sent_pixels_by_nside.values()))

    def finder_context(self) -> '_FinderContextManager':
        """Creates a context manager for startup & ending conditions."""
        return self._FinderContextManager(self._finder, self)

    class _FinderContextManager:
        def __init__(self, finder: BestPixelRecoFinder, parent: 'PixelRecoCollector'):
            self.finder = finder
            self.parent = parent

        async def __aenter__(self) -> "PixelRecoCollector._FinderContextManager":
            self.parent._in_finder_context = True
            return self

        async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:  # type: ignore[no-untyped-def]
            self.finder.finish()
            self.parent._in_finder_context = False

    async def register_sent_pixels(self, addl_sent_pixels: Set[SentPixel]) -> None:
        """Register the pixel ids recently sent.

        When `addl_sent_pixels` is empty (happens at the end of the
        scan), `self.predictive_scanning_threshold` will now be ignored.
        """
        if addl_sent_pixels:
            for sentpix in addl_sent_pixels:
                self.reporter.increment_pixels_sent_ct(sentpix.nside)
                try:
                    self._sent_pixels_by_nside[sentpix.nside].append(sentpix)
                except KeyError:
                    self._sent_pixels_by_nside[sentpix.nside] = [sentpix]

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

        # match to corresponding SentPixel
        sent_pixel = None
        for sent_pixel in self._sent_pixels_by_nside[pixreco.nside]:
            if sent_pixel.matches_pixreco(pixreco):
                break
        if not sent_pixel:
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
            roundtrip_start=sent_pixel.sent_time,
            roundtrip_end=time.time(),
        )

    def collected_everything_sent(self) -> bool:
        """Has every pixel been collected?"""
        # first check lengths, faster: O(1)
        if self.n_sent != len(self._pixrecoid_received_quick_lookup):
            return False
        # now, sanity check contents, slower: O(n)
        sent_ids = set((p.nside, p.pixel_id, p.posvar_id) for p in self.sent_pixels)
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
        for nside, sentpix in self._sent_pixels_by_nside.items():
            finished = len(self.nsides_dict[nside]) * self._finder.n_posvar
            updated_percents[nside] = finished / len(sentpix)

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


async def scan(
    scan_id: str,
    reco_algo: str,
    event_metadata: EventMetadata,
    nsides_dict: Optional[NSidesDict],
    GCDQp_packet: List[icetray.I3Frame],
    baseline_GCD: str,
    output_dir: Optional[Path],
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    nside_progression: NSideProgression,
    predictive_scanning_threshold: float,
    skydriver_rc: Optional[RestClient],
) -> NSidesDict:
    """Send pixels to be reco'd by client(s), then collect results and save to
    disk."""
    global_start_time = time.time()
    LOGGER.info(f"Starting up Skymap Scanner server for event: {event_metadata=}")

    if not nsides_dict:
        nsides_dict = {}

    pixeler = PixelsToReco(
        nsides_dict=nsides_dict,
        GCDQp_packet=GCDQp_packet,
        baseline_GCD=baseline_GCD,
        min_nside=nside_progression.min_nside,
        input_time_name=cfg.INPUT_TIME_NAME,
        input_pos_name=cfg.INPUT_POS_NAME,
        output_particle_name=cfg.OUTPUT_PARTICLE_NAME,
        reco_algo=reco_algo,
        event_metadata=event_metadata,
    )

    reporter = Reporter(
        scan_id,
        global_start_time,
        nsides_dict,
        len(pixeler.pos_variations),
        nside_progression,
        skydriver_rc,
        event_metadata,
        predictive_scanning_threshold,
    )
    await reporter.precomputing_report()

    # Start the scan iteration loop
    total_n_pixreco = await _serve_and_collect(
        to_clients_queue,
        from_clients_queue,
        reco_algo,
        nsides_dict,
        pixeler,
        reporter,
        predictive_scanning_threshold,
        nside_progression,
    )

    # sanity check
    if not total_n_pixreco:
        raise RuntimeError("No pixels were ever sent.")

    # get, log, & post final results
    result = await reporter.after_computing_report()

    # write out .npz & .json files
    if output_dir:
        npz_fpath = result.to_npz(event_metadata, output_dir)
        json_fpath = result.to_json(event_metadata, output_dir)
        LOGGER.info(f"Output Files: {npz_fpath}, {json_fpath}")

    return nsides_dict


async def _send_pixels(
    to_clients_queue: mq.Queue,
    reco_algo: str,
    pixeler: PixelsToReco,
    already_sent_pixels: Set[SentPixel],
    nside_subprogression: NSideProgression,
) -> Set[SentPixel]:
    """This send the next logical round of pixels to be reconstructed."""
    LOGGER.info("Getting pixels to send to clients...")

    sent_pixels: Set[SentPixel] = set([])
    async with to_clients_queue.open_pub() as pub:
        for i, pframe in enumerate(
            pixeler.gen_new_pixel_pframes(already_sent_pixels, nside_subprogression)
        ):
            LOGGER.info(f"Sending message M#{i} ({pframe_to_pixelrecoid(pframe)})...")
            await pub.send(
                {
                    cfg.MSG_KEY_RECO_ALGO: reco_algo,
                    cfg.MSG_KEY_PFRAME: pframe,
                }
            )
            sent_pixels.add(SentPixel.from_pframe(pframe))

    # check if anything was actually processed
    if not sent_pixels:
        LOGGER.info("No additional pixels were sent.")
    else:
        LOGGER.info(f"Done serving pixels to clients: {len(sent_pixels)}.")
    return sent_pixels


async def _serve_and_collect(
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    reco_algo: str,
    nsides_dict: NSidesDict,
    pixeler: PixelsToReco,
    reporter: Reporter,
    predictive_scanning_threshold: float,
    nside_progression: NSideProgression,
) -> int:
    """Run the next (or first) scan iteration (set of pixel-recos).

    Return the number of pixels sent. Stop when all sent pixels have
    been received (or the MQ-sub times-out).
    """
    collector = PixelRecoCollector(
        n_posvar=len(pixeler.pos_variations),
        nsides_dict=nsides_dict,
        reporter=reporter,
        predictive_scanning_threshold=predictive_scanning_threshold,
        nsides=list(nside_progression.keys()),
    )

    max_nside_to_refine = None  # start by not refining any (ie we generate first nside)
    potentiallly_done = False
    async with collector.finder_context(), from_clients_queue.open_sub() as sub:
        while True:
            #
            # SEND PIXELS -- the next logical round of pixels (not necessarily the next nside)
            #
            sent_pixels = await _send_pixels(
                to_clients_queue,
                reco_algo,
                pixeler,
                collector.sent_pixels,
                # we want to open re-refinement for all nsides <= max_nside_to_refine
                nside_progression.get_slice_plus_one(max_nside_to_refine),
            )
            # Check if scan is done --
            # we collected everything & there was no re-refinement of a region
            if potentiallly_done:
                if not sent_pixels:
                    LOGGER.info("Done receiving/saving pixel-recos from clients.")
                    return collector.n_sent
                potentiallly_done = False
            # NOTE: when `sent_pixels` is empty (and we didn't previously
            #       collect all we sent) it just means there were no addl
            #       pixels to refine this time around. That doesn't mean
            #       there won't be more in the future.
            await collector.register_sent_pixels(sent_pixels)

            #
            # COLLECT PIXEL-RECOS
            #
            LOGGER.info("Receiving pixel-recos from clients...")
            async for msg in sub:
                if not isinstance(msg['pixreco'], PixelReco):
                    raise ValueError(f"Message not {PixelReco}: {type(msg['pixreco'])}")
                try:
                    await collector.collect(msg['pixreco'], msg['runtime'])
                except ExtraPixelRecoException as e:
                    logging.error(e)

                # are we potentially done?
                if collector.collected_everything_sent():
                    LOGGER.debug("Potentially done receiving/saving pixel-recos...")
                    potentiallly_done = True
                    break

                # if we've got enough pixrecos, let's get a jump on the next round
                if max_nside_to_refine := collector.get_max_nside_to_refine():
                    LOGGER.info(f"Predictive threshold met (max={max_nside_to_refine})")
                    break

            # do-while loop logic
            if max_nside_to_refine or potentiallly_done:
                continue
            LOGGER.error("The MQ-sub must have timed out (too many MIA clients)")
            return collector.n_sent

    # this statement should never be reached
    raise RuntimeError("Unknown state -- there is a bug in the collection logic")


def write_startup_json(
    client_startup_json: Path,
    event_metadata: EventMetadata,
    nside_progression: NSideProgression,
    baseline_GCD_file: str,
    GCDQp_packet: List[icetray.I3Frame],
) -> str:
    """Write startup JSON file for client-spawning.

    Return the scan_id string.
    """
    if cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID:
        scan_id = cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID
    else:
        scan_id = (
            f"{event_metadata.event_id}-"
            f"{'-'.join(f'{n}:{x}' for n,x in nside_progression.items())}-"
            f"{int(time.time())}"
        )

    json_dict = {
        "scan_id": scan_id,
        "mq_basename": scan_id,
        "baseline_GCD_file": baseline_GCD_file,
        "GCDQp_packet": json.loads(
            full_event_followup.frame_packet_to_i3live_json(
                GCDQp_packet, pnf_framing=False
            )
        ),
    }

    with open(client_startup_json, "w") as f:
        json.dump(json_dict, f)
    LOGGER.info(
        f"Startup JSON: {client_startup_json} ({client_startup_json.stat().st_size} bytes)"
    )

    return json_dict["scan_id"]  # type: ignore[no-any-return]


def main() -> None:
    """Get command-line arguments and perform event scan via clients."""

    def _nside_and_pixelextension(val: str) -> Tuple[int, int]:
        nside, ext = val.split(":")
        return int(nside), int(ext)

    parser = argparse.ArgumentParser(
        description=(
            "Start up server to serve pixels to clients and save pixel-reconstructions "
            "from clients for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # directory args
    parser.add_argument(
        "--client-startup-json",
        required=True,
        help="The filepath to save the JSON needed to spawn clients (the parent directory must already exist)",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).parent.is_dir(),
            NotADirectoryError(Path(x).parent),
        ),
    )
    parser.add_argument(
        "-c",
        "--cache-dir",
        required=True,
        help="The cache directory to use",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_dir(),
            NotADirectoryError(x),
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="The directory to write out the .npz file",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_dir(),
            NotADirectoryError(x),
        ),
    )

    # "physics" args
    parser.add_argument(
        "--reco-algo",
        choices=recos.get_all_reco_algos(),
        help="The reconstruction algorithm to use",
    )
    parser.add_argument(
        "-e",
        "--event-file",
        default=None,
        help="The file containing the event to scan (.pkl or .json)",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            (x.endswith(".pkl") or x.endswith(".json")) and Path(x).is_file(),
            argparse.ArgumentTypeError(
                f"Invalid Event: '{x}' Event needs to be a .pkl or .json file."
            ),
        ),
    )
    parser.add_argument(
        "-g",
        "--gcd-dir",
        default=cfg.DEFAULT_GCD_DIR,
        help="The GCD directory to use",
        type=Path,
    )
    parser.add_argument(
        "--nsides",
        dest="nside_progression",
        default=NSideProgression.DEFAULT,
        help=(
            f"The progression of nside values to use, "
            f"each ':'-paired with their pixel extension value. "
            f"The first nside's pixel extension must be {NSideProgression.FIRST_NSIDE_PIXEL_EXTENSION}. "
            f"Example: --nsides 8:{NSideProgression.FIRST_NSIDE_PIXEL_EXTENSION} 64:12 512:24"
        ),
        nargs='*',
        type=_nside_and_pixelextension,
    )
    # --real-event XOR --simulated-event
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--real-event",
        action="store_true",
        help='include this flag if the event is real',
    )
    group.add_argument(
        "--simulated-event",
        action="store_true",
        help='include this flag if the event was simulated',
    )

    # predictive_scanning_threshold
    parser.add_argument(
        "--predictive-scanning-threshold",
        default=cfg.PREDICTIVE_SCANNING_THRESHOLD_DEFAULT,
        help=(
            "The percentage of reconstructed pixels collected before "
            "the next nside's round of pixels can be served"
        ),
        type=lambda x: argparse_tools.validate_arg(
            float(x),
            cfg.PREDICTIVE_SCANNING_THRESHOLD_MIN
            <= float(x)
            <= cfg.PREDICTIVE_SCANNING_THRESHOLD_MAX,
            argparse.ArgumentTypeError(
                f"value must be "
                f"[{cfg.PREDICTIVE_SCANNING_THRESHOLD_MIN}, "
                f"{cfg.PREDICTIVE_SCANNING_THRESHOLD_MAX}]: '{x}'"
            ),
        ),
    )

    args = parser.parse_args()
    logging_tools.set_level(
        cfg.ENV.SKYSCAN_LOG,  # type: ignore[arg-type]
        first_party_loggers="skyscan",
        third_party_level=cfg.ENV.SKYSCAN_LOG_THIRD_PARTY,  # type: ignore[arg-type]
        use_coloredlogs=True,
        future_third_parties=["google", "pika"],  # at most only one will be used
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # nsides
    args.nside_progression = NSideProgression(args.nside_progression)

    # check if Baseline GCD directory is reachable (also checks default value)
    if not Path(args.gcd_dir).is_dir():
        raise NotADirectoryError(args.gcd_dir)

    # make skydriver REST connection
    if cfg.ENV.SKYSCAN_SKYDRIVER_ADDRESS:
        skydriver_rc = RestClient(
            cfg.ENV.SKYSCAN_SKYDRIVER_ADDRESS, token=cfg.ENV.SKYSCAN_SKYDRIVER_AUTH
        )
    else:
        skydriver_rc = None
        if not args.output_dir:
            raise RuntimeError(
                "Must include either --output-dir or SKYSCAN_SKYDRIVER_ADDRESS (env var), "
                f"otherwise you won't see your results!"
            )

    # read event file
    event_contents = fetch_event_contents(args.event_file, skydriver_rc)

    # get inputs (load event_id + state_dict cache)
    event_metadata, state_dict = extract_json_message.extract_json_message(
        event_contents,
        reco_algo=args.reco_algo,
        is_real_event=args.real_event,
        cache_dir=str(args.cache_dir),
        GCD_dir=str(args.gcd_dir),
    )

    # write startup files for client-spawning
    scan_id = write_startup_json(
        args.client_startup_json,
        event_metadata,
        args.nside_progression,
        state_dict[cfg.STATEDICT_BASELINE_GCD_FILE],
        state_dict[cfg.STATEDICT_GCDQP_PACKET],
    )

    # make mq connections
    LOGGER.info("Making MQClient queue connections...")
    to_clients_queue = mq.Queue(
        cfg.ENV.SKYSCAN_BROKER_CLIENT,
        address=cfg.ENV.SKYSCAN_BROKER_ADDRESS,
        name=f"to-clients-{scan_id}",
        auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
        timeout=cfg.ENV.SKYSCAN_MQ_TIMEOUT_TO_CLIENTS,
    )
    from_clients_queue = mq.Queue(
        cfg.ENV.SKYSCAN_BROKER_CLIENT,
        address=cfg.ENV.SKYSCAN_BROKER_ADDRESS,
        name=f"from-clients-{scan_id}",
        auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
        timeout=cfg.ENV.SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS,
    )

    # go!
    asyncio.run(
        scan(
            scan_id=scan_id,
            reco_algo=args.reco_algo,
            event_metadata=event_metadata,
            nsides_dict=state_dict.get(cfg.STATEDICT_NSIDES),
            GCDQp_packet=state_dict[cfg.STATEDICT_GCDQP_PACKET],
            baseline_GCD=state_dict[cfg.STATEDICT_BASELINE_GCD_FILE],
            output_dir=args.output_dir,
            to_clients_queue=to_clients_queue,
            from_clients_queue=from_clients_queue,
            nside_progression=args.nside_progression,
            predictive_scanning_threshold=args.predictive_scanning_threshold,
            skydriver_rc=skydriver_rc,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
