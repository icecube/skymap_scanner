"""The Skymap Scanner Server."""

# pylint: disable=invalid-name,import-error

import argparse
import asyncio
import datetime as dt
import itertools as it
import json
import logging
import pickle
import time
from pathlib import Path, PurePosixPath
from pprint import pformat
from typing import Dict, Iterator, List, Optional, Set, Tuple

import healpy  # type: ignore[import]
import mqclient as mq
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]
    astro,
    dataclasses,
    dataio,
    full_event_followup,
    icetray,
)
from rest_tools.client import RestClient
from wipac_dev_tools import argparse_tools, logging_tools

from .. import config as cfg
from .. import recos
from ..utils import extract_json_message, pixelreco
from ..utils.icetrayless import parse_event_id
from ..utils.load_scan_state import get_baseline_gcd_frames
from ..utils.scan_result import PyDictResult, ScanResult
from ..utils.utils import get_event_mjd, pow_of_two
from . import LOGGER
from .choose_new_pixels_to_scan import choose_new_pixels_to_scan

Progress = Dict[str, Union[str, Dict[str, str]]]


class DuplicatePixelRecoException(Exception):
    """Raised when a pixel-reco (message) is received that is semantically
    equivalent to a prior.

    For example, a pixel-reco (message) that has the same NSide, Pixel
    ID, and Variation ID as an already received message.
    """


class ProgressReporter:
    """Manage various means for reporting progress during & after scanning."""

    def __init__(
        self,
        scan_id: str,
        global_start_time: float,
        nsides_dict: pixelreco.NSidesDict,
        min_nside: int,  # TODO: replace with nsides & implement
        max_nside: int,  # TODO: remove
        event_id: str,
        skydriver_rc: Optional[RestClient],
        result_metadata: dict,
    ) -> None:
        """
        Arguments:
            `scan_id`
                - the unique id of this scan
            `global_start_time`
                - the start time (epoch) of the entire scan
            `nsides_dict`
                - the nsides_dict
            `min_nside`
                - min nside value
            `max_nside`
                - max nside value
            `event_id`
                - the event id
            `skydriver_rc`
                - a connection to the SkyDriver REST interface
            `result_metadata`
                - a collection of metadata to include along with ScanResult instances

        Environment Variables:
            `SKYSCAN_PROGRESS_INTERVAL_SEC`
                - produce a progress report with this interval
            `SKYSCAN_RESULT_INTERVAL_SEC`
                - produce a (partial) skymap result with this interval
        """
        self.scan_id = scan_id
        self.global_start_time = global_start_time
        self.nsides_dict = nsides_dict
        self.skydriver_rc = skydriver_rc
        self.result_metadata = result_metadata

        self._n_pixreco: Optional[int] = None
        self._n_posvar: Optional[int] = None
        self.pixreco_ct = 0

        self.min_nside = min_nside  # TODO: replace with nsides & implement
        self.max_nside = max_nside  # TODO: remove
        self.event_id = event_id

        # all set by calling initial_report()
        self.last_time_reported = 0.0
        self.last_time_reported_skymap = 0.0
        self.reporter_start_time = 0.0
        self.time_before_reporter = 0.0
        self.global_start_time = 0.0

    async def start(self, n_pixreco: int, n_posvar: int) -> None:
        """Send an initial report/log/plot.

        Arguments:
            `n_pixreco`
                - number of expected pixel-recos
            `n_posvar`
                - number of position variations per pixel
        """
        self.n_pixreco = n_pixreco
        self.n_posvar = n_posvar
        self.pixreco_ct = 0
        self.reporter_start_time = time.time()
        self.time_before_reporter = self.reporter_start_time - self.global_start_time
        await self._report(bypass_timers=True)

    @property
    def n_pixreco(self) -> int:
        if self._n_pixreco is None:
            raise Exception("ProgressReporter instance never called 'start()'")
        return self._n_pixreco

    @n_pixreco.setter
    def n_pixreco(self, val: int) -> None:
        if val <= 0:
            raise ValueError(f"n_pixreco is not positive: {val}")
        self._n_pixreco = val

    @property
    def n_posvar(self) -> int:
        if self._n_posvar is None:
            raise Exception("ProgressReporter instance never called 'start()'")
        return self._n_posvar

    @n_posvar.setter
    def n_posvar(self, val: int) -> None:
        if val <= 0:
            raise ValueError(f"n_posvar is not positive: {val}")
        self._n_posvar = val

    async def record_pixreco(self) -> None:
        """Send reports/logs/plots if needed."""
        self.pixreco_ct += 1
        if self.pixreco_ct == 1:
            # always report the first received pixreco so we know things are rolling
            await self._report(bypass_timers=True)
        else:
            await self._report()

    async def _report(self, bypass_timers: bool = False) -> None:
        """Send reports/logs/plots if needed."""
        LOGGER.info(
            f"Collected: {self.pixreco_ct}/{self.n_pixreco} ({self.pixreco_ct/self.n_pixreco})"
        )

        # check if we need to send a report to the logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported
            > cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC
        ):
            self.last_time_reported = current_time
            await self.send_progress(self.get_progress())

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        if bypass_timers or (
            current_time - self.last_time_reported_skymap
            > cfg.ENV.SKYSCAN_RESULT_INTERVAL_SEC
        ):
            self.last_time_reported_skymap = current_time
            await self.send_result(self.get_result(), is_final=False)

    def get_result(self) -> ScanResult:
        """Get ScanResult."""
        return ScanResult.from_nsides_dict(self.nsides_dict, **self.result_metadata)

    def get_progress(self) -> Progress:
        """Make a status report string."""
        progress: Progress = {}
        if self.pixreco_ct == self.n_pixreco:
            progress['summary'] = "I am done with this scan iteration!"
        elif self.pixreco_ct:
            progress['summary'] = "I am busy scanning pixels."
        else:
            progress['summary'] = "I am starting up the next scan iteration..."

        progress['config'] = {
            'event': self.event_id,
            'min nside': self.min_nside,  # TODO: replace with nsides
            'max nside': self.max_nside,  # TODO: remove
            'position variations (reconstructions) per pixel': self.n_posvar,
        }

        progress['nsides'] = self._get_nsides_dict_progress()
        progress['processing'] = self._get_processing_progress()

        if self.pixreco_ct == 0:
            msg = "I will report back when I start getting pixel-reconstructions."
            progress['epilogue'] = msg
        elif self.pixreco_ct != self.n_pixreco:
            msg = f"I will report back again in {cfg.ENV.SKYSCAN_PROGRESS_INTERVAL_SEC} seconds."
            progress['epilogue'] = msg

        return progress

    def _get_processing_progress(self) -> Progress:
        """Get a multi-line report on processing stats."""
        elapsed = time.time() - self.reporter_start_time
        proc_stats = {
            "started": {
                'entire scan': str(
                    dt.datetime.fromtimestamp(int(self.global_start_time))
                ),
                'this iteration': str(
                    dt.datetime.fromtimestamp(int(self.reporter_start_time))
                ),
            },
            "complete": {
                'this iteration': {
                    f"{((self.pixreco_ct/self.n_pixreco)*100):.1f}% "
                    f"({self.pixreco_ct/self.n_posvar}/{self.n_pixreco/self.n_posvar} pixels, {self.pixreco_ct}/{self.n_pixreco} recos)"
                }
            },
            "elapsed runtime": {
                'this iteration': str(dt.timedelta(seconds=int(elapsed))),
                'this iteration + prior processing': str(
                    dt.timedelta(seconds=int(elapsed + self.time_before_reporter))
                ),
            },
        }
        if not self.pixreco_ct:  # we can't predict
            return proc_stats

        secs_per_pixreco = elapsed / self.pixreco_ct
        secs_predicted = elapsed / (self.pixreco_ct / self.n_pixreco)
        proc_stats.update(
            {
                'Rate': f"{dt.timedelta(seconds=int(secs_per_pixreco*self.n_posvar))} per pixel ({dt.timedelta(seconds=int(secs_per_pixreco))} per reco)",
                'predicted time left': {
                    'this iteration': str(
                        dt.timedelta(seconds=int(secs_predicted - elapsed))
                    )
                },
                'predicted total runtime': {
                    'this iteration': str(dt.timedelta(seconds=int(secs_predicted))),
                    'this iteration + prior processing': str(
                        dt.timedelta(
                            seconds=int(secs_predicted + self.time_before_reporter)
                        )
                    ),
                },
            }
        )

        return proc_stats

    def _get_nsides_dict_progress(self) -> Progress:
        """Get a multi-line progress report of the nsides_dict's contents."""
        saved = {}
        if self.nsides_dict:
            for nside in sorted(self.nsides_dict):  # sorted by nside
                saved[nside] = len(self.nsides_dict[nside])
        return {"saved pixels": saved}

    async def recos_complete(self) -> None:
        """Check if all the pixel-recos were received & make a final report."""
        if not self.pixreco_ct:
            raise RuntimeError("No pixel-reconstructions were ever received.")

        if self.pixreco_ct != self.n_pixreco:
            raise RuntimeError(
                f"Not all pixel-reconstructions were received: "
                f"{self.pixreco_ct}/{self.n_pixreco} ({self.pixreco_ct/self.n_pixreco})"
            )

        await self._report(bypass_timers=True)

    async def final_result(self, total_n_pixreco: int) -> ScanResult:
        """Get, log, and send final results to SkyDriver."""
        result = self.get_result()
        progress = {
            'summary': "The Skymap Scanner has finished.",
            'start/end': f"{dt.datetime.fromtimestamp(int(self.global_start_time))} – {dt.datetime.fromtimestamp(int(time.time()))}",
            'runtime': str(
                dt.timedelta(seconds=int(time.time() - self.global_start_time))
            ),
            'total pixel-reconstructions': total_n_pixreco,
        }
        LOGGER.info(progress)

        await self.send_result(result, is_final=True)
        await self.send_progress(progress)

        return result

    async def send_progress(self, progress: Progress) -> None:
        """Send progress to SkyDriver (if the connection is established)."""
        LOGGER.info(pformat(progress, indent=4))
        if not self.skydriver_rc:
            return

        body = {'progress': progress}
        await self.skydriver_rc.request("PATCH", f"/scan/manifest/{self.scan_id}", body)

    async def send_result(self, result: ScanResult, is_final: bool) -> None:
        """Send result to SkyDriver (if the connection is established)."""
        serialized = result.serialize()
        LOGGER.info(pformat(serialized, indent=4))
        if not self.skydriver_rc:
            return

        body = {'json_dict': serialized, 'is_final': is_final}
        await self.skydriver_rc.request("PUT", f"/scan/result/{self.scan_id}", body)


# fmt: off
class PixelsToReco:
    """Manage providing pixels to reco."""

    def __init__(
        self,
        nsides_dict: pixelreco.NSidesDict,
        GCDQp_packet: List[icetray.I3Frame],
        baseline_GCD: str,
        min_nside: int,  # TODO: replace with nsides & implement
        max_nside: int,  # TODO: remove
        input_time_name: str,
        input_pos_name: str,
        output_particle_name: str,
        mini_test_variations: bool,
        reco_algo:str
    ) -> None:
        """
        Arguments:
            `nsides_dict`
                - the nsides_dict
            `GCDQp_packet`
                - the GCDQp frame packet
            `min_nside`
                - min nside value
            `max_nside`
                - max nside value
            `input_time_name`
                - name of an I3Double to use as the vertex time for the coarsest scan
            `input_pos_name`
                - name of an I3Position to use as the vertex position for the coarsest scan
            `output_particle_name`
                - name of the output I3Particle
            `mini_test_variations`
                - whether this is a mini test scan (fewer variations)
            `reco_algo`
                - name of the reconstruction algorithm to run
        """
        self.nsides_dict = nsides_dict
        self.input_pos_name = input_pos_name
        self.input_time_name = input_time_name
        self.output_particle_name = output_particle_name
        self.reco_algo = reco_algo.lower()

        # Get Position Variations
        variation_distance = 20.*I3Units.m
        # Production Scan or Mini-Test Scan?
        if mini_test_variations:
            self.pos_variations = [
                dataclasses.I3Position(0.,0.,0.),
                dataclasses.I3Position(-variation_distance,0.,0.)
            ]
        else:
            if self.reco_algo == 'millipede_original':
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

        # Set nside values
        if max_nside < min_nside:
            raise ValueError(f"Invalid max/min nside: {max_nside=} < {min_nside=}")
        self.min_nside = min_nside # TODO: replace with nsides & implement
        self.max_nside = max_nside # TODO: remove

        # Validate & read GCDQp_packet
        p_frame = GCDQp_packet[-1]
        g_frame = get_baseline_gcd_frames(baseline_GCD, GCDQp_packet, None)[0]

        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.fallback_position = p_frame[self.input_pos_name]
        self.fallback_time = p_frame[self.input_time_name].value
        self.fallback_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_mjd = get_event_mjd(GCDQp_packet)

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

    def generate_pframes(self) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be reco'd."""

        # find pixels to refine
        pixels_to_refine = choose_new_pixels_to_scan(
            # TODO: replace with self.nsides & implement
            self.nsides_dict, min_nside=self.min_nside, max_nside=self.max_nside
        )
        if len(pixels_to_refine) == 0:
            LOGGER.info("There are no pixels to refine.")
            return
        LOGGER.debug(f"Got pixels to refine: {pixels_to_refine}")

        # sanity check nsides_dict
        for nside in self.nsides_dict:
            for pixel in self.nsides_dict[nside]:
                if (nside,pixel) in pixels_to_refine:
                    raise RuntimeError("pixel to refine is already done processing")

        # submit the pixels we need to submit
        for i, (nside, pix) in enumerate(pixels_to_refine):
            LOGGER.debug(
                f"Generating position-variations from pixel P#{i}: {(nside, pix)}"
            )
            yield from self._gen_pixel_variations(nside=nside, pixel=pix)

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

    def _gen_pixel_variations(
        self,
        nside: icetray.I3Int,
        pixel: icetray.I3Int,
    ) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be reco'd for a given `nside` and `pixel`."""

        dec, ra = healpy.pix2ang(nside, pixel)
        dec = dec - numpy.pi/2.
        zenith, azimuth = astro.equa_to_dir(ra, dec, self.event_mjd)
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
                f"({pixelreco.pixel_to_tuple(p_frame)}) ({posVariation=})..."
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
            Tuple[icetray.I3Int, icetray.I3Int], List[pixelreco.PixelReco]
        ] = {}

    def cache_and_get_best(
        self, pixreco: pixelreco.PixelReco
    ) -> Optional[pixelreco.PixelReco]:
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
        nsides_dict: pixelreco.NSidesDict,
        progress_reporter: ProgressReporter,
        pixreco_ids_sent: Set[Tuple[int, int, int]],
    ) -> None:
        self.finder = BestPixelRecoFinder(n_posvar=n_posvar)
        self.progress_reporter = progress_reporter
        self.nsides_dict = nsides_dict
        self.pixreco_ids_received: Set[Tuple[int, int, int]] = set([])
        self.pixreco_ids_sent = pixreco_ids_sent

    async def __aenter__(self) -> "PixelRecoCollector":
        await self.progress_reporter.start(
            len(self.pixreco_ids_sent), self.finder.n_posvar
        )
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:  # type: ignore[no-untyped-def]
        await self.progress_reporter.recos_complete()
        self.finder.finish()

    async def collect(self, pixreco: pixelreco.PixelReco) -> None:
        """Cache pixreco until we can save the pixel's best received reco."""
        LOGGER.debug(f"{self.nsides_dict=}")

        if pixreco.id_tuple in self.pixreco_ids_received:
            raise DuplicatePixelRecoException(
                f"Pixel-reco has already been received: {pixreco.id_tuple}"
            )
        if pixreco.id_tuple not in self.pixreco_ids_sent:
            raise DuplicatePixelRecoException(
                f"Pixel-reco received not in sent set, it is probably from an earlier iteration: {pixreco.id_tuple}"
            )

        self.pixreco_ids_received.add(pixreco.id_tuple)
        logging_id = f"S#{len(self.pixreco_ids_received) - 1}"
        LOGGER.info(f"Got a pixel-reco {logging_id} {pixreco}")

        # get best pixreco
        best = self.finder.cache_and_get_best(pixreco)
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
                raise DuplicatePixelRecoException(
                    f"NSide {best.nside} / Pixel {best.pixel} is already in nsides_dict"
                )
            self.nsides_dict[best.nside][best.pixel] = best
            LOGGER.debug(f"Saved (found during {logging_id}): {best.id_tuple} {best}")

        # report after potential save
        await self.progress_reporter.record_pixreco()


async def serve(
    scan_id: str,
    reco_algo: str,
    event_id: str,
    nsides_dict: Optional[pixelreco.NSidesDict],
    GCDQp_packet: List[icetray.I3Frame],
    baseline_GCD: str,
    output_dir: Optional[Path],
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    mini_test_variations: bool,
    min_nside: int,  # TODO: replace with nsides & implement
    max_nside: int,  # TODO: remove
    skydriver_rc: Optional[RestClient],
) -> pixelreco.NSidesDict:
    """Send pixels to be reco'd by client(s), then collect results and save to
    disk."""
    global_start_time = time.time()
    LOGGER.info(f"Starting up Skymap Scanner server for event: {event_id=}")

    if not nsides_dict:
        nsides_dict = {}

    pixeler = PixelsToReco(
        nsides_dict=nsides_dict,
        GCDQp_packet=GCDQp_packet,
        baseline_GCD=baseline_GCD,
        min_nside=min_nside,  # TODO: replace with nsides & implement
        max_nside=max_nside,  # TODO: remove
        input_time_name=cfg.INPUT_TIME_NAME,
        input_pos_name=cfg.INPUT_POS_NAME,
        output_particle_name=cfg.OUTPUT_PARTICLE_NAME,
        mini_test_variations=mini_test_variations,
        reco_algo=reco_algo,
    )

    _, _, event_type = parse_event_id(event_id)
    progress_reporter = ProgressReporter(
        scan_id,
        global_start_time,
        nsides_dict,
        min_nside,  # TODO: replace with nsides & implement
        max_nside,  # TODO: remove
        event_id,
        skydriver_rc,
        dict(
            run_id=pixeler.event_header.run_id,
            event_id=pixeler.event_header.event_id,
            mjd=pixeler.event_mjd,
            event_type=event_type,
        ),
    )

    # Start the scan iteration loop
    total_n_pixreco = 0
    for i in it.count():
        logging.info(f"Starting new scan iteration (#{i})")
        n_pixreco = await serve_scan_iteration(
            to_clients_queue,
            from_clients_queue,
            reco_algo,
            nsides_dict,
            pixeler,
            progress_reporter,
        )
        if not n_pixreco:  # we're done
            break
        total_n_pixreco += n_pixreco

    # sanity check
    if not total_n_pixreco:
        raise RuntimeError("No pixels were ever sent.")

    # get, log, & post final results
    result = await progress_reporter.final_result(total_n_pixreco)

    # write out .npz file
    if output_dir:
        npz_fpath = result.to_npz(event_id, output_dir)
        LOGGER.info(f"Output File: {PurePosixPath(npz_fpath).name}")

    return nsides_dict


async def serve_scan_iteration(
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    reco_algo: str,
    nsides_dict: pixelreco.NSidesDict,
    pixeler: PixelsToReco,
    progress_reporter: ProgressReporter,
) -> int:
    """Run the next (or first) scan iteration (set of pixel-recos).

    Return the number of pixels sent. Stop when this is 0.
    """

    #
    # SEND PIXELS
    #

    # get pixels & send to client(s)
    LOGGER.info("Getting pixels to send to clients...")
    pixreco_ids_sent = set([])
    async with to_clients_queue.open_pub() as pub:
        for i, pframe in enumerate(pixeler.generate_pframes()):  # queue_to_clients
            _tup = pixelreco.pixel_to_tuple(pframe)
            LOGGER.info(f"Sending message M#{i} ({_tup})...")
            await pub.send(
                {
                    cfg.MSG_KEY_RECO_ALGO: reco_algo,
                    cfg.MSG_KEY_PFRAME: pframe,
                }
            )
            pixreco_ids_sent.add(_tup)

    # check if anything was actually processed
    if not pixreco_ids_sent:
        LOGGER.info("No pixels were sent for this iteration.")
        return 0
    LOGGER.info(f"Done serving pixel-variations to clients: {len(pixreco_ids_sent)}.")

    #
    # COLLECT PIXEL-RECOS
    #

    collector = PixelRecoCollector(
        n_posvar=len(pixeler.pos_variations),
        nsides_dict=nsides_dict,
        progress_reporter=progress_reporter,
        pixreco_ids_sent=pixreco_ids_sent,
    )

    # get pixel-recos from client(s), collect and save
    LOGGER.info("Receiving pixel-recos from clients...")
    async with collector as col:  # enter collector 1st for detecting when no pixel-recos received
        async with from_clients_queue.open_sub() as sub:
            async for pixreco in sub:
                if not isinstance(pixreco, pixelreco.PixelReco):
                    raise ValueError(
                        f"Message not {pixelreco.PixelReco}: {type(pixreco)}"
                    )
                try:
                    await col.collect(pixreco)
                except DuplicatePixelRecoException as e:
                    logging.error(e)
                # if we've got all the pixrecos, no need to wait for queue's timeout
                if col.pixreco_ids_sent == col.pixreco_ids_received:
                    break

    LOGGER.info("Done receiving/saving pixel-recos from clients.")
    return len(pixreco_ids_sent)


def write_startup_json(
    startup_json_dir: Path,
    event_id: str,
    min_nside: int,  # TODO: replace with nsides & implement
    max_nside: int,  # TODO: remove
    baseline_GCD_file: str,
    GCDQp_packet: List[icetray.I3Frame],
) -> str:
    """Write startup JSON file for client-spawning.

    Return the scan_id string.
    """
    json_file = startup_json_dir / "startup.json"

    if cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID:
        scan_id = cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID
    else:
        # TODO: replace with nsides & implement
        # scan_id = f"{event_id}-{'-'.join(f'{n}:{x}' for n,x in nsides)}-{int(time.time())}"
        scan_id = f"{event_id}-{min_nside}-{max_nside}-{int(time.time())}"

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

    with open(json_file, "w") as f:
        json.dump(json_dict, f)
    LOGGER.info(f"Startup JSON: {json_file} ({json_file.stat().st_size} bytes)")

    return json_dict["scan_id"]  # type: ignore[no-any-return]


def main() -> None:
    """Get command-line arguments and perform event scan via clients."""

    def _nside_and_pixelextension(val: str) -> Tuple[int, int]:
        nside, ext = val.split(":")
        return pow_of_two(nside), int(ext)

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
        "--startup-json-dir",
        required=True,
        help="The dir to save the JSON needed to spawn clients",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_dir(),
            NotADirectoryError(x),
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
        required=True,
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
        default=[
            (cfg.MIN_NSIDE_DEFAULT, 12),
            (cfg.MAX_NSIDE_DEFAULT, 24),
        ],  # TODO: [(8,12), (64,12), (512,24)]
        help=(
            "The nside values to use for each iteration, "
            "each ':'-paired with their pixel extension value. "
            "Example: --nsides 8:12 64:12 512:24"
        ),
        nargs='*',
        type=_nside_and_pixelextension,
    )

    # testing/debugging args
    parser.add_argument(
        "--mini-test-variations",
        default=False,
        action="store_true",
        help="run w/ minimal variations for testing (mini-scale)",
    )

    # skydriver
    parser.add_argument(
        "--skydriver",
        default="",
        help="The SkyDriver REST interface URL to connect to",
    )

    # mq args
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The MQ broker URL to connect to",
    )
    parser.add_argument(
        "--timeout-to-clients",
        default=60 * 1,
        type=int,
        help="timeout (seconds) for messages TO client(s)",
    )
    parser.add_argument(
        "--timeout-from-clients",
        default=60 * 30,
        type=int,
        help="timeout (seconds) for messages FROM client(s)",
    )

    # logging args
    parser.add_argument(
        "-l",
        "--log",
        default="INFO",
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default="WARNING",
        help="the output logging level for third-party loggers",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        args.log,
        first_party_loggers="skyscan",
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
        future_third_parties=["google", "pika"],  # at most only one will be used
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # nsides
    args.nsides = sorted(args.nsides)
    if list(set(n[0] for n in args.nsides)) != [n[0] for n in args.nsides]:
        raise argparse.ArgumentTypeError(
            f"'--nsides' cannot contain duplicate nsides: {args.nsides}"
        )
    # TODO - actually implement variable nside sequences (https://github.com/icecube/skymap_scanner/issues/79)
    # for now...
    if len(args.nsides) > 2:
        raise argparse.ArgumentTypeError("'--nsides' cannot contain more than 2 values")
    min_nside = args.nsides[0][0]
    max_nside = args.nsides[-1][0]  # if only one value, then also grab index-0
    logging.warning(
        f"VARIABLE NSIDE SEQUENCES NOT YET IMPLEMENTED: using {min_nside=} & {max_nside=} with default pixel-extension values"
    )

    # check if Baseline GCD directory is reachable (also checks default value)
    if not Path(args.gcd_dir).is_dir():
        raise NotADirectoryError(args.gcd_dir)

    # read event file
    if args.event_file.suffix == ".json":
        # json
        with open(args.event_file, "r") as f:
            event_contents = json.load(f)
    else:
        # pickle
        with open(args.event_file, "rb") as f:
            event_contents = pickle.load(f)

    # get inputs (load event_id + state_dict cache)
    event_id, state_dict = extract_json_message.extract_json_message(
        event_contents,
        reco_algo=args.reco_algo,
        filestager=dataio.get_stagers(),
        cache_dir=str(args.cache_dir),
        override_GCD_filename=str(args.gcd_dir),
    )

    # write startup files for client-spawning
    scan_id = write_startup_json(
        args.startup_json_dir,
        event_id,
        min_nside,  # TODO: replace with args.nsides & implement
        max_nside,  # TODO: remove
        state_dict[cfg.STATEDICT_BASELINE_GCD_FILE],
        state_dict[cfg.STATEDICT_GCDQP_PACKET],
    )

    # make mq connections
    LOGGER.info("Making MQClient queue connections...")
    to_clients_queue = mq.Queue(
        "pulsar",
        address=args.broker,
        name=f"to-clients-{scan_id}",
        auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
        timeout=args.timeout_to_clients,
    )
    from_clients_queue = mq.Queue(
        "pulsar",
        address=args.broker,
        name=f"from-clients-{scan_id}",
        auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
        timeout=args.timeout_from_clients,
    )

    # make skydriver REST connection
    if args.skydriver:
        skydriver_rc = RestClient(args.skydriver, token=cfg.ENV.SKYSCAN_SKYDRIVER_AUTH)
    else:
        skydriver_rc = None
        if not args.output_dir:
            raise RuntimeError(
                "Must include either --output-dir or --skydriver, otherwise you won't see your results!"
            )

    # go!
    asyncio.run(
        serve(
            scan_id=scan_id,
            reco_algo=args.reco_algo,
            event_id=event_id,
            nsides_dict=state_dict.get(cfg.STATEDICT_NSIDES),
            GCDQp_packet=state_dict[cfg.STATEDICT_GCDQP_PACKET],
            baseline_GCD=state_dict[cfg.STATEDICT_BASELINE_GCD_FILE],
            output_dir=args.output_dir,
            to_clients_queue=to_clients_queue,
            from_clients_queue=from_clients_queue,
            mini_test_variations=args.mini_test_variations,
            min_nside=min_nside,  # TODO: replace with args.nsides & implement
            max_nside=max_nside,  # TODO: remove
            skydriver_rc=skydriver_rc,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
