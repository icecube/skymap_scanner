"""The Server.

Based on:
    python/perform_scan.py
        - a lot of similar code
    cloud_tools/send_scan.py (just the Pulsar logic)
        - send_scan_icetray() vs send_scan()
        - Pulsar logic
    cloud_tools/collect_pixels.py
        - collect_and_save_pixels_icetray() vs collect_and_save_pixels()
        - Pulsar logic
    cloud_tools/save_pixels.py
        - not much in common
"""

# fmt: off

import argparse
import asyncio
import logging
import os
import pickle
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import asyncstdlib as asl
import healpy  # type: ignore[import]
import mqclient_pulsar as mq
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]
from wipac_dev_tools import logging_tools

from .. import extract_json_message
from ..utils import (
    StateDict,
    get_event_mjd,
    pixel_to_tuple,
    save_GCD_frame_packet_to_file,
)
from .choose_new_pixels_to_scan import choose_new_pixels_to_scan

NSidePixelPair = Tuple[icetray.I3Int, icetray.I3Int]

LOGGER = logging.getLogger("skyscan-server")


class ProgressReporter:
    """Manage various means for reporting progress during event scanning."""

    def __init__(
        self,
        state_dict: StateDict,
        npixels: int,
        logger: Callable[[Any], None] = print,
        logging_interval_in_seconds: int = 5*60,
        skymap_plotting_callback: Optional[Callable[[StateDict], None]] = None,
        skymap_plotting_callback_interval_in_seconds: int = 30*60,
    ) -> None:
        """
        Arguments:
            `state_dict`
                - the state_dict
            `npixels`
                - number of expected pixels
            `logger`
                - a callback function for semi-verbose logging
            `logging_interval_in_seconds`
                - call the logger callback with this interval
            `skymap_plotting_callback`
                - a callback function the receives the full current state of the map
            `skymap_plotting_callback_interval_in_seconds`
                - a callback function the receives the full
        """
        self.state_dict = state_dict
        self.logger = logger

        if logging_interval_in_seconds <= 0:
            raise ValueError(
                f"logging_interval_in_seconds is not positive: {logging_interval_in_seconds}"
            )
        self.logging_interval_in_seconds = logging_interval_in_seconds

        self.skymap_plotting_callback = skymap_plotting_callback

        if skymap_plotting_callback_interval_in_seconds <= 0:
            raise ValueError(
                f"skymap_plotting_callback_interval_in_seconds is not positive: {skymap_plotting_callback_interval_in_seconds}"
            )
        self.skymap_plotting_callback_interval_in_seconds = skymap_plotting_callback_interval_in_seconds

        if npixels <= 0:
            raise ValueError(f"npixels is not positive: {npixels}")
        self.npixels = npixels

        self.count = 0
        self.last_time_reported = time.time()
        self.last_time_reported_skymap = time.time()

    def report(self, override_timestamp: bool = False) -> None:
        """Send reports/logs/plots if needed."""
        self.count += 1
        LOGGER.info(f"Collected: {self.count}/{self.npixels} ({self.count/self.npixels})")

        # check if we need to send a report to the logger
        current_time = time.time()
        elapsed_seconds = current_time - self.last_time_reported
        if override_timestamp or elapsed_seconds > self.logging_interval_in_seconds:
            self.last_time_reported = current_time
            self.send_status_report()

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        elapsed_seconds = current_time - self.last_time_reported_skymap
        if override_timestamp or elapsed_seconds > self.skymap_plotting_callback_interval_in_seconds:
            self.last_time_reported_skymap = current_time
            if self.skymap_plotting_callback is not None:
                self.skymap_plotting_callback(self.state_dict)

    def send_status_report(self) -> None:
        # TODO - update with count (count of current or total? both?)
        num_pixels_in_process = float("inf")
        # num_pixels_in_process = len(self.pixels_in_process)
        message = "I am busy scanning pixels. {0} pixels are currently being processed.\n".format(num_pixels_in_process)

        if len(self.state_dict["nsides"])==0:
            message += " - no pixels are done yet\n"
        else:
            for nside in self.state_dict["nsides"]:
                pixels = self.state_dict["nsides"][nside]
                message += " - {0} pixels of nside={1}\n".format( len(pixels), nside )

        message += "I will report back again in {0} seconds.".format(self.logging_interval_in_seconds)

        self.logger(message)

    def finish(self) -> None:
        """Check if all the scans were received & make a final report."""
        if not self.count:
            raise RuntimeError("No scans were ever received.")

        if self.count != self.npixels:
            raise RuntimeError(
                f"Not all scans were received: "
                f"{self.count}/{self.npixels} ({self.count/self.npixels})"
            )

        self.report(override_timestamp=True)


class PixelsToScan:
    """Manage providing pixels to scan."""

    def __init__(
        self,
        state_dict: StateDict,
        input_time_name: str = "HESE_VHESelfVetoVertexTime",
        input_pos_name: str = "HESE_VHESelfVetoVertexPos",
        output_particle_name: str = "MillipedeSeedParticle",
        finish_function: Optional[Callable[[StateDict], None]] = None,
        mini_test_scan: bool = False,
    ) -> None:
        """
        Arguments:
            `state_dict`
                - the state_dict
            `input_time_name`
                - name of an I3Double to use as the vertex time for the coarsest scan
            `input_pos_name`
                - name of an I3Position to use as the vertex position for the coarsest scan
            `output_particle_name`
                - name of the output I3Particle
            `finish_function`
                - function to be run once scan is finished. handles final plotting
            `mini_test_scan`
                - whether this is a mini test scan (fewer variations)
        """
        self.state_dict = state_dict
        self.input_pos_name = input_pos_name
        self.input_time_name = input_time_name
        self.output_particle_name = output_particle_name
        self.finish_function = finish_function

        variationDistance = 20.*I3Units.m
        if mini_test_scan:  # Use Just 2 Variations for Mini-Test Scan
            self.posVariations = [
                dataclasses.I3Position(0.,0.,0.),
                dataclasses.I3Position(-variationDistance,0.,0.)
            ]
        else:
            self.posVariations = [
                dataclasses.I3Position(0.,0.,0.),
                dataclasses.I3Position(-variationDistance,0.,0.),
                dataclasses.I3Position( variationDistance,0.,0.),
                dataclasses.I3Position(0.,-variationDistance,0.),
                dataclasses.I3Position(0., variationDistance,0.),
                dataclasses.I3Position(0.,0.,-variationDistance),
                dataclasses.I3Position(0.,0., variationDistance)
            ]

        # Production Scan or Mini-Test Scan?
        if mini_test_scan:
            self.min_nside = 1
        else:
            self.min_nside = 8

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
        if self.min_nside == 1:  # (mini test scan)
            pixels_to_refine = choose_new_pixels_to_scan(
                self.state_dict, min_nside=self.min_nside, max_nside=1
            )
        else:
            pixels_to_refine = choose_new_pixels_to_scan(
                self.state_dict, min_nside=self.min_nside
            )
        if len(pixels_to_refine) == 0:
            raise RuntimeError("There are no pixels to refine.")
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

        for i in range(0,len(self.posVariations)):
            posVariation = self.posVariations[i]
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
        NPosVar: int,  # Number of position variations to collect
    ) -> None:
        if NPosVar <= 0:
            raise ValueError(f"NPosVar is not positive: {NPosVar}")
        self.NPosVar = NPosVar

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

        if len(self.pixelNumToFramesMap[index]) >= self.NPosVar:
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
                f"{self.count}/{self.npixels} ({self.count/self.npixels}): "
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

        # insert scan into state_dict
        if nside not in self.state_dict["nsides"]:
            self.state_dict["nsides"][nside] = {}
        if pixel in self.state_dict["nsides"][nside]:
            raise RuntimeError("NSide {0} / Pixel {1} is already in state_dict".format(nside, pixel))
        self.state_dict["nsides"][nside][pixel] = dict(frame=frame, llh=llh)

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
    def __init__(
        self,
        NPosVar: int,  # Number of position variations to collect
        npixels: int,  # Number of expected pixels
        state_dict: StateDict,
        event_id: str,
        cache_dir: str,
    ) -> None:
        self.finder = FindBestRecoResultForPixel(
            NPosVar=NPosVar,
        )
        self.saver = SaveRecoResults(
            state_dict=state_dict,
            event_id=event_id,
            cache_dir=cache_dir,
        )
        self.progress_reporter = ProgressReporter(
            state_dict,
            npixels,
            logger=print,
            logging_interval_in_seconds=5 * 60,
            skymap_plotting_callback=None,
            skymap_plotting_callback_interval_in_seconds=30 * 60,
        )
        self.scans_received: List[Tuple[int, int, int]] = []

    def __enter__(self) -> "ScanCollector":
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
        self.progress_reporter.report()

        best_scan = self.finder.cache_and_get_best(scan)
        LOGGER.info(f"Cached scan {scan_id} {scan_tuple}")

        if not best_scan:
            LOGGER.debug(f"Best scan not yet found ({scan_id}) {scan_tuple}")
            return
        LOGGER.info(
            f"Saving a BEST scan (found during {scan_id}): "
            f"{pixel_to_tuple(best_scan)} {best_scan}"
        )
        self.saver.save(best_scan)
        LOGGER.debug(f"Saved (found during {scan_id}): {pixel_to_tuple(best_scan)}")


async def serve_pixel_scans(
    event_id_string: str,
    state_dict: StateDict,
    cache_dir: str,
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
    timeout_s_to_clients: int,  # for pulsar
    timeout_s_from_clients: int,  # for pulsar
    mini_test_scan: bool,
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
    LOGGER.info("Making MQClient queue connections...")
    to_clients_queue = mq.Queue(
        address=broker,
        name=topic_to_clients,
        auth_token=auth_token,
        timeout=timeout_s_to_clients,
    )
    from_clients_queue = mq.Queue(
        address=broker,
        name=topic_from_clients,
        auth_token=auth_token,
        timeout=timeout_s_from_clients,
    )

    #
    # SEND PIXELS
    #

    pixeler = PixelsToScan(state_dict=state_dict, mini_test_scan=mini_test_scan)

    # get pixels & send to client(s)
    LOGGER.info("Getting pixels to send to clients...")
    async with to_clients_queue.open_pub() as pub:
        for i, pframe in enumerate(pixeler.generate_pframes()):  # topic_to_clients
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
        npixels = i + 1  # 0-indexing :) # pylint: disable=undefined-loop-variable
    except NameError as e:
        raise RuntimeError("No pixels were sent.") from e
    LOGGER.info(f"Done serving pixels to clients: {npixels}.")

    #
    # COLLECT SCANS
    #

    collector = ScanCollector(
        NPosVar=len(pixeler.posVariations),
        npixels=npixels,
        state_dict=state_dict,
        event_id=event_id_string,
        cache_dir=cache_dir,
    )

    # get scans from client(s), collect and save
    LOGGER.info("Receiving scans from clients...")
    async with from_clients_queue.open_sub() as sub:
        with collector as col:
            async for i, scan in asl.enumerate(sub):
                col.collect(scan)
                # if we've got all the scans, no need to wait for queue's timeout
                if i == npixels - 1:
                    break

    LOGGER.info("Done receiving/saving scans from clients.")


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
        "--event-pkl",
        required=True,
        help=(
            "The pickle (.pkl) file containing the event to scan. "
            "The basename is used as a suffix for pulsar topics."
        ),
        type=lambda x: _validate_arg(
            x,
            x.endswith(".pkl") and os.path.isfile(x),
            argparse.ArgumentTypeError(
                f"Invalid Event: {x}. Event needs to be a .pkl file."
            ),
        ),
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

    # testing/debugging args
    parser.add_argument(
        "--mini-test-scan",
        default=False,
        action="store_true",
        help="run a mini scan for testing (fewer pixels, variations, etc.)",
    )

    # pulsar args
    parser.add_argument(
        "-t",
        "--topics-root",
        default="",
        help="A root/prefix to base topic names for communicating to/from client(s)",
    )
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The Pulsar broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
        help="The Pulsar authentication token to use",
    )
    parser.add_argument(
        "--timeout-pub",
        dest="timeout_s_to_clients",
        default=60 * 1,
        help="timeout (seconds) for sending messages TO client(s)",
    )
    parser.add_argument(
        "--timeout-sub",
        dest="timeout_s_from_clients",
        default=60 * 30,
        help="timeout (seconds) for receiving messages FROM client(s)",
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
        first_party_loggers=[LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    with open(args.event_pkl, "rb") as f:
        event_contents = pickle.load(f)

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
            event_id_string=event_id,
            state_dict=state_dict,
            cache_dir=args.cache_dir,
            broker=args.broker,
            auth_token=args.auth_token,
            topic_to_clients=os.path.join(
                args.topics_root, f"to-clients-{os.path.basename(args.event_pkl)}"
            ),
            topic_from_clients=os.path.join(
                args.topics_root, f"from-clients-{os.path.basename(args.event_pkl)}"
            ),
            timeout_s_to_clients=args.timeout_s_to_clients,
            timeout_s_from_clients=args.timeout_s_from_clients,
            mini_test_scan=args.mini_test_scan,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
