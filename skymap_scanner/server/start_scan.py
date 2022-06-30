"""The Server.

Based on:
    python/perform_scan.py
        - a lot of similar code
    cloud_tools/send_scan.py (just the MQ logic)
        - send_scan_icetray() vs send_scan()
        - MQ logic
    cloud_tools/collect_pixels.py
        - collect_and_save_pixels_icetray() vs collect_and_save_pixels()
        - MQ logic
    cloud_tools/save_pixels.py
        - not much in common
"""


import argparse
import asyncio
import datetime as dt
import json
import logging
import os
import pickle
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import asyncstdlib as asl
import healpy  # type: ignore[import]
import mqclient_pulsar as mq
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]
from wipac_dev_tools import logging_tools

from .. import extract_json_message
from ..load_scan_state import get_baseline_gcd_frames, get_reco_losses_inside
from ..utils import (
    StateDict,
    get_event_mjd,
    pixel_to_tuple,
    save_GCD_frame_packet_to_file,
)
from .choose_new_pixels_to_scan import (
    MAX_NSIDE_DEFAULT,
    MIN_NSIDE_DEFAULT,
    choose_new_pixels_to_scan,
)
from .scan_result import ScanResult

NSidePixelPair = Tuple[icetray.I3Int, icetray.I3Int]

LOGGER = logging.getLogger("skyscan-server")


class SlackInterface:
    """Dummy class for now."""

    active = False


def is_pow_of_two(value: Union[int, float]) -> bool:
    """Return whether `value` is an integer power of two [1, 2, 4, ...)."""
    if isinstance(value, float):
        if not value.is_integer():  # type: ignore[union-attr]
            return False
        value = int(value)

    if not isinstance(value, int):
        return False

    # I know, I know, no one likes bit shifting... buuuut...
    return (value != 0) and (value & (value - 1) == 0)


class ProgressReporter:
    """Manage various means for reporting progress during event scanning."""

    def __init__(
        self,
        state_dict: StateDict,
        nscans: int,
        nposvar: int,
        min_nside: int,
        max_nside: int,
        event_id: str,
        slack_interface: SlackInterface,
        report_interval_in_seconds: int = 5 * 60,
        skymap_plotting_interval_in_seconds: int = 30 * 60,
    ) -> None:
        """
        Arguments:
            `state_dict`
                - the state_dict
            `nscans`
                - number of expected scans
            `nposvar`
                - number of potion variations per pixel
            `min_nside`
                - min nside value
            `max_nside`
                - max nside value
            `event_id`
                - the event id
            `slack_interface`
                - a connection to Slack
            `report_interval_in_seconds`
                - make a report with this interval
            `skymap_plotting_interval_in_seconds`
                - make a skymap plot with this interval
        """
        self.state_dict = state_dict
        self.slack_interface = slack_interface

        if report_interval_in_seconds <= 0:
            raise ValueError(
                f"report_interval_in_seconds is not positive: {report_interval_in_seconds}"
            )
        self.report_interval_in_seconds = report_interval_in_seconds

        if skymap_plotting_interval_in_seconds <= 0:
            raise ValueError(
                f"skymap_plotting_interval_in_seconds is not positive: {skymap_plotting_interval_in_seconds}"
            )
        self.skymap_plotting_interval_in_seconds = skymap_plotting_interval_in_seconds

        if nscans <= 0:
            raise ValueError(f"nscans is not positive: {nscans}")
        self.nscans = nscans

        if nposvar <= 0:
            raise ValueError(f"nposvar is not positive: {nposvar}")
        self.nposvar = nposvar

        self.min_nside = min_nside
        self.max_nside = max_nside
        self.event_id = event_id

        self.scan_ct = 0

        # all set by calling initial_report()
        self.last_time_reported = 0.0
        self.last_time_reported_skymap = 0.0
        self.scan_start_time = 0.0
        self.time_before_scan = 0

    def initial_report(self, global_start_time: float) -> None:
        """Send an initial report/log/plot."""
        self.scan_start_time = time.time()
        self.time_before_scan = int(self.scan_start_time - global_start_time)
        self._report(override_timestamp=True)

    def record_scan(self) -> None:
        """Send reports/logs/plots if needed."""
        self.scan_ct += 1
        if self.scan_ct == 1:
            # always report the first received scan so we know things are rolling
            self._report(override_timestamp=True)
        else:
            self._report()

    def final_report(self) -> None:
        """Send a final, complete report/log/plot."""
        self._report(override_timestamp=True)

    def _report(self, override_timestamp: bool = False) -> None:
        """Send reports/logs/plots if needed."""
        LOGGER.info(
            f"Collected: {self.scan_ct}/{self.nscans} ({self.scan_ct/self.nscans})"
        )

        # check if we need to send a report to the logger
        current_time = time.time()
        elapsed_seconds = current_time - self.last_time_reported
        if override_timestamp or elapsed_seconds > self.report_interval_in_seconds:
            self.last_time_reported = current_time
            status_report = self.get_status_report()
            if self.slack_interface.active:
                self.slack_interface.post(status_report)
            LOGGER.info(status_report)

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        elapsed_seconds = current_time - self.last_time_reported_skymap
        if (
            override_timestamp
            or elapsed_seconds > self.skymap_plotting_interval_in_seconds
        ):
            self.last_time_reported_skymap = current_time
            if self.slack_interface.active:
                self.slack_interface.post_skymap_plot(self.state_dict)

    def get_status_report(self) -> str:
        """Make a status report string."""
        if self.scan_ct == self.nscans:
            message = "I am done scanning this refinement iteration!\n\n"
        elif self.scan_ct:
            message = "I am busy scanning pixels.\n\n"
        else:
            message = "I am starting up the next refinement iteration...\n\n"

        message += (
            f"{self.get_state_dict_report()}"  # ends w/ '\n'
            "Config:\n"
            f" - event: {self.event_id}\n"
            f" - min nside: {self.min_nside}\n"
            f" - max nside: {self.max_nside}\n"
            f" - position variations per pixel: {self.nposvar}\n"
            f"{self.get_processing_stats_report()}"  # ends w/ '\n'
            f"\n"
        )

        if self.scan_ct == 0:
            message += "I will report back when I start getting scans."
        elif self.scan_ct != self.nscans:
            message += f"I will report back again in {self.report_interval_in_seconds} seconds."

        return message

    def get_processing_stats_report(self) -> str:
        """Get a multi-line report on processing stats."""
        elapsed = int(time.time() - self.scan_start_time)
        msg = (
            "Processing Stats:\n"
            f" - {((self.scan_ct/self.nscans)*100):.1f}% "
            f"({self.scan_ct/self.nposvar}/{self.nscans/self.nposvar} pixels, "
            f"{self.scan_ct}/{self.nscans} scans) [this iteration]\n"
            f" - Elapsed Runtime\n"
            f"    * {dt.timedelta(seconds=elapsed)} [this iteration]\n"
            f"    * {dt.timedelta(seconds=elapsed+self.time_before_scan)} [this iteration + prior processing]\n"
        )
        if not self.scan_ct:  # we can't predict
            return msg

        secs_per_scan = elapsed / self.scan_ct
        secs_predicted = elapsed / (self.scan_ct / self.nscans)
        msg += (
            f" - Rate\n"
            f"    * {secs_per_scan/60*self.nposvar:.2f} min/pixel ({secs_per_scan/60:.2f} min/scan)\n"
            f" - Predicted Time Left\n"
            f"    * {dt.timedelta(seconds=int(secs_predicted-elapsed))} [this iteration]\n"
            f" - Predicted Total Runtime\n"
            f"    * {dt.timedelta(seconds=int(secs_predicted))} [this iteration]\n"
            f"    * {dt.timedelta(seconds=int(secs_predicted+self.time_before_scan))} [this iteration + prior processing]\n"
        )
        return msg

    def get_state_dict_report(self) -> str:
        """Get a multi-line progress report of the state_dict's nside contents."""
        msg = "Iterations with Saved Pixels:\n"
        if not self.state_dict["nsides"]:
            msg += " - no pixels are done yet\n"
        else:

            def nside_line(nside: int, npixels: int) -> str:
                return f" - {npixels} pixels, nside={nside}\n"

            for nside in sorted(self.state_dict["nsides"]):  # sorted by nside
                msg += nside_line(nside, len(self.state_dict["nsides"][nside]))

        return msg

    def finish(self) -> None:
        """Check if all the scans were received & make a final report."""
        if not self.scan_ct:
            raise RuntimeError("No scans were ever received.")

        if self.scan_ct != self.nscans:
            raise RuntimeError(
                f"Not all scans were received: "
                f"{self.scan_ct}/{self.nscans} ({self.scan_ct/self.nscans})"
            )

        self.final_report()


# fmt: off
class PixelsToScan:
    """Manage providing pixels to scan."""

    def __init__(
        self,
        state_dict: StateDict,
        min_nside: int,
        max_nside: int,
        input_time_name: str = "HESE_VHESelfVetoVertexTime",
        input_pos_name: str = "HESE_VHESelfVetoVertexPos",
        output_particle_name: str = "MillipedeSeedParticle",
        mini_test_variations: bool = False,
    ) -> None:
        """
        Arguments:
            `state_dict`
                - the state_dict
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
        """
        self.state_dict = state_dict
        self.input_pos_name = input_pos_name
        self.input_time_name = input_time_name
        self.output_particle_name = output_particle_name

        # Get Position Variations
        variation_distance = 20.*I3Units.m
        # Production Scan or Mini-Test Scan?
        if mini_test_variations:
            self.pos_variations = [
                dataclasses.I3Position(0.,0.,0.),
                dataclasses.I3Position(-variation_distance,0.,0.)
            ]
        else:
            self.pos_variations = [
                dataclasses.I3Position(0.,0.,0.),
                dataclasses.I3Position(-variation_distance,0.,0.),
                dataclasses.I3Position( variation_distance,0.,0.),
                dataclasses.I3Position(0.,-variation_distance,0.),
                dataclasses.I3Position(0., variation_distance,0.),
                dataclasses.I3Position(0.,0.,-variation_distance),
                dataclasses.I3Position(0.,0., variation_distance)
            ]

        # Set nside values
        if max_nside < min_nside:
            raise ValueError(f"Invalid max/min nside: {max_nside=} < {min_nside=}")
        self.min_nside = min_nside
        self.max_nside = max_nside

        # Validate & read state_dict
        if "GCDQp_packet" not in self.state_dict:
            raise RuntimeError("\"GCDQp_packet\" not in state_dict.")

        if "baseline_GCD_file" not in self.state_dict:
            raise RuntimeError("\"baseline_GCD_file\" not in state_dict.")

        if "nsides" not in self.state_dict:
            self.state_dict["nsides"] = {}

        p_frame = self.state_dict["GCDQp_packet"][-1]
        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.fallback_position = p_frame[self.input_pos_name]
        self.fallback_time = p_frame[self.input_time_name].value
        self.fallback_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_mjd = get_event_mjd(self.state_dict)  # type: ignore[no-untyped-call]

    def generate_pframes(self) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be scanned."""

        # find pixels to refine
        pixels_to_refine = choose_new_pixels_to_scan(
            self.state_dict, min_nside=self.min_nside, max_nside=self.max_nside
        )
        if len(pixels_to_refine) == 0:
            LOGGER.info("There are no pixels to refine.")
            return
        LOGGER.debug(f"Got pixels to refine: {pixels_to_refine}")

        # sanity check state_dict
        for nside in self.state_dict["nsides"]:
            for pixel in self.state_dict["nsides"][nside]:
                if (nside,pixel) in pixels_to_refine:
                    raise RuntimeError("pixel to refine is already done processing")

        # submit the pixels we need to submit
        for i, (nside, pix) in enumerate(pixels_to_refine):
            LOGGER.debug(
                f"Generating position-variations from pixel P#{i}: {(nside, pix)}"
            )
            yield from self._gen_pixel_variations(nside=nside, pixel=pix)

    def _gen_pixel_variations(
        self,
        nside: icetray.I3Int,
        pixel: icetray.I3Int,
    ) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be scanned for a given `nside` and `pixel`."""

        # print "Scanning nside={0}, pixel={1}".format(nside,pixel)

        dec, ra = healpy.pix2ang(nside, pixel)
        dec = dec - numpy.pi/2.
        zenith, azimuth = astro.equa_to_dir(ra, dec, self.event_mjd)
        zenith = float(zenith)
        azimuth = float(azimuth)
        direction = dataclasses.I3Direction(zenith,azimuth)

        # test-case-scan: this whole part is different
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

                if coarser_nside in self.state_dict["nsides"]:
                    if coarser_pixel in self.state_dict["nsides"][coarser_nside]:
                        # coarser pixel found
                        break

            if coarser_nside < self.min_nside:
                # no coarser pixel is available (probably we are just scanning finely around MC truth)
                position = self.fallback_position
                time = self.fallback_time
                energy = self.fallback_energy
            else:
                if numpy.isnan(self.state_dict["nsides"][coarser_nside][coarser_pixel]["llh"]):
                    # coarser reconstruction failed
                    position = self.fallback_position
                    time = self.fallback_time
                    energy = self.fallback_energy
                else:
                    coarser_frame = self.state_dict["nsides"][coarser_nside][coarser_pixel]["frame"]
                    coarser_particle = coarser_frame["MillipedeStarting2ndPass"]
                    position = coarser_particle.pos
                    time = coarser_particle.time
                    energy = coarser_particle.energy

        for i in range(0,len(self.pos_variations)):
            posVariation = self.pos_variations[i]
            p_frame = icetray.I3Frame(icetray.I3Frame.Physics)

            thisPosition = dataclasses.I3Position(position.x + posVariation.x,position.y + posVariation.y,position.z + posVariation.z)

            # generate the particle from scratch
            particle = dataclasses.I3Particle()
            particle.shape = dataclasses.I3Particle.ParticleShape.InfiniteTrack
            particle.fit_status = dataclasses.I3Particle.FitStatus.OK
            particle.pos = thisPosition
            particle.dir = direction
            particle.time = time
            particle.energy = energy
            p_frame[self.output_particle_name] = particle

            # generate a new event header
            eventHeader = dataclasses.I3EventHeader(self.event_header)
            eventHeader.sub_event_stream = "SCAN_nside%04u_pixel%04u_posvar%04u" % (nside, pixel, i)
            eventHeader.sub_event_id = int(pixel)
            p_frame["I3EventHeader"] = eventHeader
            p_frame["SCAN_HealpixPixel"] = icetray.I3Int(int(pixel))
            p_frame["SCAN_HealpixNSide"] = icetray.I3Int(int(nside))
            p_frame["SCAN_PositionVariationIndex"] = icetray.I3Int(int(i))

            LOGGER.debug(
                f"Yielding PFrame (pixel position-variation) PV#{i} "
                f"({pixel_to_tuple(p_frame)}) ({posVariation=})..."
            )
            yield p_frame


class FindBestRecoResultForPixel:
    """Facilitate finding the best reco scan result."""

    def __init__(
        self,
        nposvar: int,  # Number of position variations to collect
    ) -> None:
        if nposvar <= 0:
            raise ValueError(f"nposvar is not positive: {nposvar}")
        self.nposvar = nposvar

        self.pixelNumToFramesMap: Dict[NSidePixelPair, icetray.I3Frame] = {}

    def cache_and_get_best(self, frame: icetray.I3Frame) -> Optional[icetray.I3Frame]:
        """Add frame to internal cache and possibly return the best scan for pixel.

        If all the scans for the embedded pixel have be received,
        return the best one. Otherwise, return None.
        """
        if "SCAN_HealpixNSide" not in frame:
            raise RuntimeError("SCAN_HealpixNSide not in frame")
        if "SCAN_HealpixPixel" not in frame:
            raise RuntimeError("SCAN_HealpixPixel not in frame")
        if "SCAN_PositionVariationIndex" not in frame:
            raise RuntimeError("SCAN_PositionVariationIndex not in frame")

        nside = frame["SCAN_HealpixNSide"].value
        pixel = frame["SCAN_HealpixPixel"].value
        index = (nside,pixel)
        posVarIndex = frame["SCAN_PositionVariationIndex"].value

        if index not in self.pixelNumToFramesMap:
            self.pixelNumToFramesMap[index] = []
        self.pixelNumToFramesMap[index].append(frame)

        if len(self.pixelNumToFramesMap[index]) >= self.nposvar:
            # print "all scans arrived for pixel", index
            bestFrame = None
            bestFrameLLH = None
            for frame in self.pixelNumToFramesMap[index]:
                if "MillipedeStarting2ndPass_millipedellh" in frame:
                    thisLLH = frame["MillipedeStarting2ndPass_millipedellh"].logl
                else:
                    thisLLH = numpy.nan
                # print "  * llh =", thisLLH
                if (bestFrame is None) or ((thisLLH < bestFrameLLH) and (not numpy.isnan(thisLLH))):
                    bestFrame=frame
                    bestFrameLLH=thisLLH

            # print "all scans arrived for pixel", index, "best LLH is", bestFrameLLH

            if bestFrame is None:
                # just push the first frame if all of them are nan
                bestFrame = self.pixelNumToFramesMap[index][0]

            del self.pixelNumToFramesMap[index]
            return bestFrame

        return None

    def finish(self) -> None:
        """Check if all the scans were received.

        If an entire pixel (and all its scans) was dropped by client(s),
        this will not catch it.
        """
        if len(self.pixelNumToFramesMap) != 0:
            raise RuntimeError(
                f"Pixels left in cache, not all of the packets seem to be complete: "
                f"{self.pixelNumToFramesMap}"
            )


class SaveRecoResults:
    """Facilitate saving reco scan results to disk."""

    def __init__(
        self,
        state_dict: StateDict,
        event_id: str,
        cache_dir: str,
    ) -> None:
        self.state_dict = state_dict
        self.this_event_cache_dir = os.path.join(cache_dir, event_id)

    def save(self, frame: icetray.I3Frame) -> icetray.I3Frame:
        """Save scan to disk as .i3 file at `self.this_event_cache_dir`.

        Raise errors for invalid frame or already saved scan.

        Makes dirs as needed.
        """
        if "SCAN_HealpixNSide" not in frame:
            raise RuntimeError("SCAN_HealpixNSide not in frame")
        if "SCAN_HealpixPixel" not in frame:
            raise RuntimeError("SCAN_HealpixPixel not in frame")
        if "SCAN_PositionVariationIndex" not in frame:
            raise RuntimeError("SCAN_PositionVariationIndex not in frame")

        nside = frame["SCAN_HealpixNSide"].value
        pixel = frame["SCAN_HealpixPixel"].value
        index = (nside,pixel)

        if "MillipedeStarting2ndPass" not in frame:
            raise RuntimeError("\"MillipedeStarting2ndPass\" not found in reconstructed frame")
        if "MillipedeStarting2ndPass_millipedellh" not in frame:
            llh = numpy.nan
            # raise RuntimeError("\"MillipedeStarting2ndPass_millipedellh\" not found in reconstructed frame")
        else:
            llh = frame["MillipedeStarting2ndPass_millipedellh"].logl

        """
        Calculate reco losses, based on load_scan_state()
        """
        # apparently baseline GCD is sufficient here
        # maybe filestager can be None
        geometry = get_baseline_gcd_frames(self.state_dict, filestager=dataio.get_stagers())[0]
        
        try:
            recoLossesInside, recoLossesTotal = get_reco_losses_inside(p_frame=frame, g_frame=geometry)
        except KeyError:
            LOGGER.error(f"Missing attribute in Geometry frame: {KeyError}")
            LOGGER.info(f"Frame contains the following keys {geometry.keys()}")
            raise

        # insert scan into state_dict
        if nside not in self.state_dict["nsides"]:
            self.state_dict["nsides"][nside] = {}
        if pixel in self.state_dict["nsides"][nside]:
            raise RuntimeError("NSide {0} / Pixel {1} is already in state_dict".format(nside, pixel))
        self.state_dict["nsides"][nside][pixel] = dict(frame=frame, llh=llh, recoLossesInside=recoLossesInside, recoLossesTotal=recoLossesTotal)

        # save this frame to the disk cache

        nside_dir = os.path.join(self.this_event_cache_dir, "nside{0:06d}".format(nside))
        if not os.path.exists(nside_dir):
            os.mkdir(nside_dir)
        pixel_file_name = os.path.join(nside_dir, "pix{0:012d}.i3".format(pixel))

        # print " - saving pixel file {0}...".format(pixel_file_name)
        save_GCD_frame_packet_to_file([frame], pixel_file_name)

        return frame


# fmt: on
class ScanCollector:
    """Manage the collecting, filtering, reporting, and saving of scan results."""

    def __init__(
        self,
        nposvar: int,  # Number of position variations to collect
        nscans: int,  # Number of expected pixels
        min_nside: int,
        max_nside: int,
        state_dict: StateDict,
        event_id: str,
        cache_dir: str,
        global_start_time: float,
        slack_interface: SlackInterface,
    ) -> None:
        self.finder = FindBestRecoResultForPixel(
            nposvar=nposvar,
        )
        self.saver = SaveRecoResults(
            state_dict=state_dict,
            event_id=event_id,
            cache_dir=cache_dir,
        )
        self.progress_reporter = ProgressReporter(
            state_dict,
            nscans,
            nposvar,
            min_nside,
            max_nside,
            event_id,
            slack_interface,
            report_interval_in_seconds=5 * 60,
            skymap_plotting_interval_in_seconds=30 * 60,
        )
        self.global_start_time = global_start_time
        self.scans_received: List[Tuple[int, int, int]] = []

    def __enter__(self) -> "ScanCollector":
        self.progress_reporter.initial_report(self.global_start_time)
        return self

    def __exit__(self, *args: Any) -> None:
        self.progress_reporter.finish()
        self.finder.finish()

    def collect(self, scan: icetray.I3Frame) -> None:
        """Cache scan until we can save the pixel's best received scan, for each pixel."""
        LOGGER.debug(f"{self.saver.state_dict=}")

        scan_tuple = pixel_to_tuple(scan)
        if scan_tuple in self.scans_received:
            raise ValueError(f"Scan has already been received: {scan_tuple}")
        self.scans_received.append(scan_tuple)
        scan_id = f"S#{len(self.scans_received) - 1}"
        LOGGER.info(f"Got a scan {scan_id} {scan_tuple}: {scan}")

        # get best scan
        best_scan = self.finder.cache_and_get_best(scan)
        LOGGER.info(f"Cached scan {scan_id} {scan_tuple}")

        # save best scan (if we got it)
        if not best_scan:
            LOGGER.debug(f"Best scan not yet found ({scan_id}) {scan_tuple}")
        else:
            LOGGER.info(
                f"Saving a BEST scan (found during {scan_id}): "
                f"{pixel_to_tuple(best_scan)} {best_scan}"
            )
            self.saver.save(best_scan)
            LOGGER.debug(f"Saved (found during {scan_id}): {pixel_to_tuple(best_scan)}")

        # report after potential save
        self.progress_reporter.record_scan()


async def serve_pixel_scans(
    event_id: str,
    state_dict: StateDict,
    cache_dir: str,
    output_dir: str,
    broker: str,  # for mq
    auth_token: str,  # for mq
    queue_to_clients: str,  # for mq
    queue_from_clients: str,  # for mq
    timeout_to_clients: int,  # for mq
    timeout_from_clients: int,  # for mq
    mini_test_variations: bool,
    min_nside: int,
    max_nside: int,
) -> None:
    """Send pixels to be scanned by client(s), then collect scans and save to disk

    Based on:
        python/perform_scan.py
        cloud_tools/send_scan.py

    Based on:
        python/perform_scan.py
        cloud_tools/collect_pixels.py
        cloud_tools/save_pixels.py (only nominally)
    """
    global_start_time = time.time()
    LOGGER.info(f"Starting up Skymap Scanner server for event: {event_id=}")

    LOGGER.info("Making MQClient queue connections...")
    to_clients_queue = mq.Queue(
        address=broker,
        name=queue_to_clients,
        auth_token=auth_token,
        timeout=timeout_to_clients,
    )
    from_clients_queue = mq.Queue(
        address=broker,
        name=queue_from_clients,
        auth_token=auth_token,
        timeout=timeout_from_clients,
    )

    pixeler = PixelsToScan(
        state_dict=state_dict,
        mini_test_variations=mini_test_variations,
        min_nside=min_nside,
        max_nside=max_nside,
    )

    slack_interface = SlackInterface()

    # Start the refinement-iteration loop
    total_nscans = 0
    while True:
        logging.info("Starting new refinement iteration")
        nscans = await refinement_iteration(
            to_clients_queue,
            from_clients_queue,
            event_id,
            state_dict,
            cache_dir,
            global_start_time,
            pixeler,
            slack_interface,
        )
        if not nscans:  # we're done
            break
        total_nscans += nscans

    # sanity check
    if not total_nscans:
        raise RuntimeError("No pixels were ever sent.")

    # write out .npz file
    result = ScanResult.from_state_dict(state_dict)
    npz_fpath = result.save(event_id, output_dir)

    # log & post final slack message
    final_message = (
        f"All refinement iterations / scans complete.\n"
        f"Runtime: {dt.timedelta(seconds=int(global_start_time - time.time()))}\n"
        f"Total Millipede Scans: {total_nscans}\n"
        f"Output File: {os.path.basename(npz_fpath)}"
    )
    LOGGER.info(final_message)
    if slack_interface.active:
        slack_interface.post(final_message)
        slack_interface.post_skymap_plot(state_dict)


async def refinement_iteration(
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    event_id: str,
    state_dict: StateDict,
    cache_dir: str,
    global_start_time: float,
    pixeler: PixelsToScan,
    slack_interface: SlackInterface,
) -> int:
    """Run the next (or first) refinement iteration set of scans.

    Return the number of pixels sent. Stop when this is 0.
    """

    #
    # SEND PIXELS
    #

    # get pixels & send to client(s)
    LOGGER.info("Getting pixels to send to clients...")
    async with to_clients_queue.open_pub() as pub:
        for i, pframe in enumerate(pixeler.generate_pframes()):  # queue_to_clients
            LOGGER.info(f"Sending message M#{i} ({pixel_to_tuple(pframe)})...")
            await pub.send(
                {
                    "Pixel_PFrame": pframe,
                    "GCDQp_Frames": state_dict["GCDQp_packet"],
                    "base_GCD_filename_url": state_dict["baseline_GCD_file"],
                }
            )

    # check if anything was actually processed
    try:
        nscans = i + 1  # 0-indexing :) # pylint: disable=undefined-loop-variable
    except NameError:
        LOGGER.info("No pixels were sent for this iteration.")
        return 0
    LOGGER.info(f"Done serving pixel-variations to clients: {nscans}.")

    #
    # COLLECT SCANS
    #

    collector = ScanCollector(
        nposvar=len(pixeler.pos_variations),
        nscans=nscans,
        min_nside=pixeler.min_nside,
        max_nside=pixeler.max_nside,
        state_dict=state_dict,
        event_id=event_id,
        cache_dir=cache_dir,
        global_start_time=global_start_time,
        slack_interface=slack_interface,
    )

    # get scans from client(s), collect and save
    LOGGER.info("Receiving scans from clients...")
    with collector as col:  # enter collector 1st for detecting when no scans received
        async with from_clients_queue.open_sub() as sub:
            async for i, scan in asl.enumerate(sub):
                col.collect(scan)
                # if we've got all the scans, no need to wait for queue's timeout
                if i == nscans - 1:
                    break

    LOGGER.info("Done receiving/saving scans from clients.")
    return nscans


def main() -> None:
    """Get command-line arguments and serve pixel-scans to clients."""
    parser = argparse.ArgumentParser(
        description=(
            "Start up server to serve up pixels to and save millipede scans "
            "from n clients for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def _validate_arg(val: str, test: bool, exc: Exception) -> str:
        """Validation `val` by checking `test` and raise `exc` if that is falsy."""
        if test:
            return val
        raise exc

    # "physics" args
    parser.add_argument(
        "-e",
        "--event-file",
        required=True,
        help="The file containing the event to scan (.pkl or .json)",
        type=lambda x: _validate_arg(
            x,
            (x.endswith(".pkl") or x.endswith(".json")) and os.path.isfile(x),
            argparse.ArgumentTypeError(
                f"Invalid Event: '{x}' Event needs to be a .pkl or .json file."
            ),
        ),
    )
    parser.add_argument(
        "--event-mqname",
        required=True,
        help="identifier to correspond to the event for MQ connections",
    )
    parser.add_argument(
        "-c",
        "--cache-dir",
        required=True,
        help="The cache directory to use",
        type=lambda x: _validate_arg(
            x,
            os.path.isdir(x),
            argparse.ArgumentTypeError(f"NotADirectoryError: {x}"),
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="The directory to write out the .npz file",
        type=lambda x: _validate_arg(
            x,
            os.path.isdir(x),
            argparse.ArgumentTypeError(f"NotADirectoryError: {x}"),
        ),
    )
    parser.add_argument(
        "-g",
        "--gcd-dir",
        required=True,
        help="The GCD directory to use",
        type=lambda x: _validate_arg(
            x,
            os.path.isdir(x),
            argparse.ArgumentTypeError(f"NotADirectoryError: {x}"),
        ),
    )
    parser.add_argument(
        "--min-nside",
        default=MIN_NSIDE_DEFAULT,
        help="The first refinement iteration's nside value",
        type=lambda x: int(
            _validate_arg(
                x,
                x.isnumeric() and is_pow_of_two(int(x)),
                argparse.ArgumentTypeError(
                    f"--min-nside must be an integer power of two (not {x})"
                ),
            ),
        ),
    )
    parser.add_argument(
        "--max-nside",
        default=MAX_NSIDE_DEFAULT,
        help="The final refinement iteration's nside value",
        type=lambda x: int(
            _validate_arg(
                x,
                x.isnumeric() and is_pow_of_two(int(x)),
                argparse.ArgumentTypeError(
                    f"--max-nside must be an integer power of two (not {x})"
                ),
            )
        ),
    )

    # testing/debugging args
    parser.add_argument(
        "--mini-test-variations",
        default=False,
        action="store_true",
        help="run w/ minimal variations for testing (mini-scale)",
    )

    # mq args
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The MQ broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
        help="The MQ authentication token to use",
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
        args.log.upper(),
        first_party_loggers=[LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    if args.event_file.endswith(".json"):
        # json
        with open(args.event_file, "r") as fj:
            event_contents = json.load(fj)
    else:
        # pickle
        with open(args.event_file, "rb") as fp:
            event_contents = pickle.load(fp)

    # get inputs (load event_id + state_dict cache)
    event_id, state_dict = extract_json_message.extract_json_message(
        event_contents,
        filestager=dataio.get_stagers(),
        cache_dir=args.cache_dir,
        override_GCD_filename=args.gcd_dir,
    )

    # go!
    asyncio.get_event_loop().run_until_complete(
        serve_pixel_scans(
            event_id=event_id,
            state_dict=state_dict,
            cache_dir=args.cache_dir,
            output_dir=args.output_dir,
            broker=args.broker,
            auth_token=args.auth_token,
            queue_to_clients=f"to-clients-{os.path.basename(args.event_mqname)}",
            queue_from_clients=f"from-clients-{os.path.basename(args.event_mqname)}",
            timeout_to_clients=args.timeout_to_clients,
            timeout_from_clients=args.timeout_from_clients,
            mini_test_variations=args.mini_test_variations,
            min_nside=args.min_nside,
            max_nside=args.max_nside,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
