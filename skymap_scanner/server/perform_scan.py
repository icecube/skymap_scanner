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
# pylint: skip-file

import argparse
import asyncio
import logging
import os
import pickle
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

import coloredlogs  # type: ignore[import]
import healpy  # type: ignore[import]
import mqclient_pulsar as mq
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]

from .. import extract_json_message
from ..load_scan_state import load_cache_state
from ..utils import StateDict, get_event_mjd, save_GCD_frame_packet_to_file
from .choose_new_pixels_to_scan import choose_new_pixels_to_scan

NSidePixelPair = Tuple[icetray.I3Int, icetray.I3Int]


class PixelsToScan:
    """Manage providing pixels to scan."""

    def __init__(
        self,
        state_dict: StateDict,
        input_time_name: str = "HESE_VHESelfVetoVertexTime",
        input_pos_name: str = "HESE_VHESelfVetoVertexPos",
        output_particle_name: str = "MillipedeSeedParticle",
        logger: Callable[[Any], None] = print,
        logging_interval_in_seconds: int = 5*60,
        skymap_plotting_callback: Optional[Callable[[StateDict], None]] = None,
        skymap_plotting_callback_interval_in_seconds: int = 30*60,
        finish_function: Optional[Callable[[StateDict], None]] = None,
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
            `logger`
                - a callback function for semi-verbose logging
            `logging_interval_in_seconds`
                - call the logger callback with this interval
            `skymap_plotting_callback`
                - a callback function the receives the full current state of the map
            `skymap_plotting_callback_interval_in_seconds`
                - a callback function the receives the full
            `finish_function`
                - function to be run once scan is finished. handles final plotting
        """
        self.state_dict = state_dict
        self.input_pos_name = input_pos_name
        self.input_time_name = input_time_name
        self.output_particle_name = output_particle_name
        self.logger = logger
        self.logging_interval_in_seconds = logging_interval_in_seconds
        self.skymap_plotting_callback = skymap_plotting_callback
        self.skymap_plotting_callback_interval_in_seconds = skymap_plotting_callback_interval_in_seconds
        self.finish_function = finish_function

        if "GCDQp_packet" not in self.state_dict:
            raise RuntimeError("\"GCDQp_packet\" not in state_dict.")

        # self.GCDQpFrames = self.state_dict["GCDQp_packet"]

        if "baseline_GCD_file" not in self.state_dict:
            raise RuntimeError("\"baseline_GCD_file\" not in state_dict.")
        # self.baseline_GCD_file = self.state_dict["baseline_GCD_file"]

        if "nsides" not in self.state_dict:
            self.state_dict["nsides"] = {}
        self.nsides = self.state_dict["nsides"]

        p_frame = self.state_dict["GCDQp_packet"][-1]
        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.fallback_position = p_frame[self.input_pos_name]
        self.fallback_time = p_frame[self.input_time_name].value
        self.fallback_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_mjd = get_event_mjd(self.state_dict)  # type: ignore[no-untyped-call]

        self.pixels_in_process: Set[NSidePixelPair] = set()

        self.last_time_reported = time.time()
        self.last_time_reported_skymap = time.time()

    def send_status_report(self) -> None:
        num_pixels_in_process = len(self.pixels_in_process)
        message = "I am busy scanning pixels. {0} pixels are currently being processed.\n".format(num_pixels_in_process)

        if len(self.state_dict["nsides"])==0:
            message += " - no pixels are done yet\n"
        else:
            for nside in self.state_dict["nsides"]:
                pixels = self.state_dict["nsides"][nside]
                message += " - {0} pixels of nside={1}\n".format( len(pixels), nside )

        message += "I will report back again in {0} seconds.".format(self.logging_interval_in_seconds)

        self.logger(message)

    def generate_pframes(self) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be scanned."""

        # push GCDQp packet if not done so already
        # if self.GCDQpFrames:
        #     for frame in self.GCDQpFrames:
        #         self.PushFrame(frame)
        #     self.GCDQpFrames = None
        #     self.logger("Commencing full-sky scan. I will first need to start up the condor jobs, this might take a while...".format())
        #     return

        # check if we need to send a report to the logger
        current_time = time.time()
        elapsed_seconds = current_time - self.last_time_reported
        if elapsed_seconds > self.logging_interval_in_seconds:
            self.last_time_reported = current_time
            self.send_status_report()

        # check if we need to send a report to the skymap logger
        current_time = time.time()
        elapsed_seconds = current_time - self.last_time_reported_skymap
        if elapsed_seconds > self.skymap_plotting_callback_interval_in_seconds:
            self.last_time_reported_skymap = current_time
            if self.skymap_plotting_callback is not None:
                self.skymap_plotting_callback(self.state_dict)

        # see if we think we are processing pixels but they have finished since
        for nside in self.state_dict["nsides"]:
            for pixel in self.state_dict["nsides"][nside]:
                if (nside,pixel) in self.pixels_in_process:
                    self.pixels_in_process.remove( (nside,pixel) )

        # find pixels to refine
        pixels_to_refine: List[NSidePixelPair] = choose_new_pixels_to_scan(self.state_dict)  # type: ignore[no-untyped-call]

        if len(pixels_to_refine) == 0:
            logging.debug("** there are no pixels left to refine. stopping.")
            if self.finish_function is not None:
                self.finish_function(self.state_dict)

            self.RequestSuspension()  # TODO - what's the non-icetray equivalent?
            return

        for nside in self.state_dict["nsides"]:
            for pixel in self.state_dict["nsides"][nside]:
                if (nside,pixel) in pixels_to_refine:
                    raise RuntimeError("pixel to refine is already done processing")

        pixels_to_submit = []
        for pixel in pixels_to_refine:
            if pixel not in self.pixels_in_process:
                pixels_to_submit.append(pixel)

        # submit the pixels we need to submit
        for nside_pix in pixels_to_submit:
            self.pixels_in_process.add(nside_pix)  # record the fact that we are processing this pixel
            yield from self._gen_for_nside_pixel(nside=nside_pix[0], pixel=nside_pix[1])

    def _gen_for_nside_pixel(
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

        if nside == 8:
            position = self.fallback_position
            time = self.fallback_time
            energy = self.fallback_energy
        else:
            coarser_nside = nside
            while True:
                coarser_nside = coarser_nside/2
                coarser_pixel = healpy.ang2pix(int(coarser_nside), dec+numpy.pi/2., ra)

                if coarser_nside < 8:
                    raise RuntimeError("internal error. cannot find an original coarser pixel for nside={0}/pixel={1}".format(nside, pixel))

                if coarser_nside in self.state_dict["nsides"]:
                    if coarser_pixel in self.state_dict["nsides"][coarser_nside]:
                        # coarser pixel found
                        break

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

        variationDistance = 20.*I3Units.m
        posVariations = [dataclasses.I3Position(0.,0.,0.),
                         dataclasses.I3Position(-variationDistance,0.,0.),
                         dataclasses.I3Position( variationDistance,0.,0.),
                         dataclasses.I3Position(0.,-variationDistance,0.),
                         dataclasses.I3Position(0., variationDistance,0.),
                         dataclasses.I3Position(0.,0.,-variationDistance),
                         dataclasses.I3Position(0.,0., variationDistance)]

        for i in range(0,len(posVariations)):
            posVariation = posVariations[i]
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

            yield p_frame


class FindBestRecoResultForPixel:
    """Facilitate finding the best reco scan result."""

    def __init__(
        self,
        NPosVar: int = 7,  # Number of position variations to collect
    ) -> None:
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
                return self.pixelNumToFramesMap[index][0]
            else:
                return bestFrame

            del self.pixelNumToFramesMap[index]

        return None

    def finish(self) -> None:
        """Check if all the scans were received.

        If an entire pixel (and all its scans) was dropped by client(s),
        this will not catch it.
        """
        if len(self.pixelNumToFramesMap) == 0:
            return

        logging.warning("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
        logging.warning(self.pixelNumToFramesMap)
        logging.warning("**** WARN ****  --  END")


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


async def serve_pixel_scans(
    event_id_string: str,
    state_dict: StateDict,
    cache_dir: str,
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    producer_name: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
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
    logging.info("Making MQClient queue connections...")
    to_clients_queue = mq.Queue(address=broker, name=topic_to_clients, auth_token=auth_token)
    from_clients_queue = mq.Queue(address=broker, name=topic_from_clients, auth_token=auth_token)

    pixeler = PixelsToScan(state_dict=state_dict)

    def makeSurePulsesExist(frame: icetray.I3Frame) -> None:
        pulsesName = "SplitUncleanedInIcePulsesLatePulseCleaned"
        if pulsesName not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName+"TimeWindows" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeWindows"))
        if pulsesName+"TimeRange" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeRange"))

    # get pixels & send to client(s)
    logging.info("Getting pixels to send to clients...")
    async with to_clients_queue.open_pub() as pub:
        for pframe in pixeler.generate_pframes():  # topic_to_clients
            logging.info(f"Got a pixel to send: {str(pframe)}")
            makeSurePulsesExist(pframe)
            pub.send(
                {
                    "Pixel_PFrame": pframe,
                    "GCDQp_Frames": state_dict["GCDQp_packet"],
                    "base_GCD_filename_url": state_dict["baseline_GCD_file"],
                }
            )
    logging.info("Done serving pixels to clients.")

    finder = FindBestRecoResultForPixel()
    saver = SaveRecoResults(
        state_dict=state_dict,
        event_id=event_id_string,
        cache_dir=cache_dir
    )

    # get scans from client(s), collect and save
    logging.info("Receiving scans from clients...")
    async with from_clients_queue.open_sub() as sub:
        async for scan in sub:
            logging.info(f"Got a scan: {str(scan)}")
            best_scan = finder.cache_and_get_best(scan)
            if not best_scan:
                continue
            logging.info(f"Saving a BEST scan: {str(best_scan)}")
            saver.save(best_scan)

    logging.info("Done receiving/saving scans from clients.")
    finder.finish()


# fmt: on
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
        "-l",
        "--log",
        default="INFO",
        help="the output logging level",
    )

    args = parser.parse_args()
    coloredlogs.install(level=args.log)
    for arg, val in vars(args).items():
        logging.warning(f"{arg}: {val}")

    with open(args.event_pkl, "rb") as f:
        event_contents = pickle.load(f)

    # load event_id + state_dict cache
    event_id, state_dict = extract_json_message.extract_json_message(
        event_contents,
        filestager=dataio.get_stagers(),
        cache_dir=args.cache_dir,
        override_GCD_filename=args.gcd_dir,
    )

    asyncio.get_event_loop().run_until_complete(
        serve_pixel_scans(
            event_id_string=event_id,
            state_dict=state_dict,
            cache_dir=args.cache_dir,
            broker=args.broker,
            auth_token=args.auth_token,
            producer_name=f"SKYSCAN-PRODUCER-{os.path.basename(args.event_pkl)}",
            topic_to_clients=os.path.join(
                args.topics_root, f"to-clients-{os.path.basename(args.event_pkl)}"
            ),
            topic_from_clients=os.path.join(
                args.topics_root, f"from-clients-{os.path.basename(args.event_pkl)}"
            ),
        )
    )
    logging.info("Done.")


if __name__ == "__main__":
    main()
