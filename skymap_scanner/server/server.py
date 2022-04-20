"""The Server.

Based on python/perform_scan.py
"""

# fmt: off
# pylint: skip-file

import os
import time
from optparse import OptionParser
from typing import Iterator

import healpy  # type: ignore[import]
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]

from .choose_new_pixels_to_scan import choose_new_pixels_to_scan
from .load_scan_state import load_cache_state
from .utils import get_event_mjd, save_GCD_frame_packet_to_file


class NothingToSendException(Exception):
    """Raise this when there is nothing (more) to send."""


class WaitingForAllScansException(Exception):
    """Raise this when not all scans for a pixel have been received."""


def simple_print_logger(text):
    print(text)


class PixelsToScan:  # formerly: `SendPixelsToScan`
    """Manage getting pixels for processing."""

    def __init__(
        self,
        state_dict=None,  # The state_dict
        InputTimeName="HESE_VHESelfVetoVertexTime",  # Name of an I3Double to use as the vertex time for the coarsest scan
        InputPosName="HESE_VHESelfVetoVertexPos",  # Name of an I3Position to use as the vertex position for the coarsest scan
        OutputParticleName="MillipedeSeedParticle",  # Name of the output I3Particle
        MaxPixelsInProcess=1000,  # Do not submit more pixels than this to the downstream module
        logger=simple_print_logger,  # a callback function for semi-verbose logging
        logging_interval_in_seconds=5*60,  # call the logger callback with this interval
        skymap_plotting_callback=None,  # a callback function the receives the full current state of the map
        skymap_plotting_callback_interval_in_seconds=30*60,
        finish_function=None  # function to be run once scan is finished. handles final plotting
    ):
        self.state_dict = state_dict
        self.input_pos_name = InputPosName
        self.input_time_name = InputTimeName
        self.output_particle_name = OutputParticleName
        self.max_pixels_in_process = MaxPixelsInProcess
        self.logger = logger
        self.logging_interval_in_seconds = logging_interval_in_seconds
        self.skymap_plotting_callback = skymap_plotting_callback
        self.skymap_plotting_callback_interval_in_seconds = skymap_plotting_callback_interval_in_seconds
        self.finish_function = finish_function

        if "GCDQp_packet" not in self.state_dict:
            raise RuntimeError("\"GCDQp_packet\" not in state_dict.")

        self.GCDQpFrames = self.state_dict["GCDQp_packet"]

        if "baseline_GCD_file" not in self.state_dict:
            raise RuntimeError("\"baseline_GCD_file\" not in state_dict.")
        self.baseline_GCD_file = self.state_dict["baseline_GCD_file"]

        if "nsides" not in self.state_dict:
            self.state_dict["nsides"] = {}
        self.nsides = self.state_dict["nsides"]

        p_frame = self.GCDQpFrames[-1]
        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.fallback_position = p_frame[self.input_pos_name]
        self.fallback_time = p_frame[self.input_time_name].value
        self.fallback_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_mjd = get_event_mjd(self.state_dict)

        self.pixels_in_process = set()

        self.last_time_reported = time.time()
        self.last_time_reported_skymap = time.time()

    def send_status_report(self):
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

    def do_process(self) -> Iterator[icetray.I3Frame]:
        """Yield PFrames (including initial GCDQpFrames)."""

        # push GCDQp packet if not done so already
        if self.GCDQpFrames:
            for frame in self.GCDQpFrames:
                yield frame
            self.GCDQpFrames = None
            return

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
        pixels_to_refine = choose_new_pixels_to_scan(self.state_dict)

        if len(pixels_to_refine) == 0:
            print("** there are no pixels left to refine. stopping.")
            if self.finish_function is not None:
                self.finish_function(self.state_dict)
            raise NothingToSendException()

        for nside in self.state_dict["nsides"]:
            for pixel in self.state_dict["nsides"][nside]:
                if (nside,pixel) in pixels_to_refine:
                    raise RuntimeError("pixel to refine is already done processing")

        pixels_to_submit = []
        for pixel in pixels_to_refine:
            if pixel not in self.pixels_in_process:
                pixels_to_submit.append(pixel)

        something_was_submitted = False

        # submit the pixels we need to submit
        for nside_pix in pixels_to_submit:
            if len(self.pixels_in_process) > self.max_pixels_in_process:
                # too many pixels in process. let some of them finish before sending more requests
                break
            self.pixels_in_process.add(nside_pix) # record the fact that we are processing this pixel
            yield from self.create_pframe(nside=nside_pix[0], pixel=nside_pix[1])
            something_was_submitted = True

        if not something_was_submitted:
            # there are submitted pixels left that haven't yet arrived

            # print "** all pixels are processing. waiting one second..."
            time.sleep(1)

            # send a special frame type to I3Distribute in order to flush its
            # output queue
            # TODO - would analogous logic be needed?
            yield icetray.I3Frame( icetray.I3Frame.Stream('\x05') )

    def create_pframe(self, nside, pixel) -> Iterator[icetray.I3Frame]:
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
    """Manage finding the best reco result for a pixel for multiple scans.

    Cache necessary info for successive calls to `do_physics()`.
    """

    def __init__(
        self,
        NPosVar=7,  # Number of position variations to collect
    ):
        self.NPosVar = NPosVar

        self.pixelNumToFramesMap = {}

    def do_physics(self, frame) -> icetray.I3Frame:
        """Once `NPosVar`-number of scans have arrived for a pixel, return best result.

        If all the scans for a pixel have not been received (yet), cache
        internally, and raise `NothingToSendException`.
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

        # not all results have been received yet for pixel
        raise WaitingForAllScansException()

    def do_finish(self) -> None:
        if len(self.pixelNumToFramesMap) == 0:
            return

        print("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
        print((self.pixelNumToFramesMap))
        print("**** WARN ****  --  END")
        raise RuntimeError("pixels left in cache, not all of the packets seem to be complete")


class SaveRecoResults:  # formerly: 'CollectRecoResults'
    """Manage saving reco results for multiple scans.

    Cache necessary info for successive calls to `do_physics()`.
    """

    def __init__(
        self,
        state_dict=None,  # The state_dict
        event_id=None,  # The event_id
        cache_dir=None,  # The cache_dir
    ):
        self.state_dict = state_dict
        self.event_id = event_id
        self.cache_dir = cache_dir

        self.this_event_cache_dir = os.path.join(self.cache_dir, self.event_id)

    def do_physics(self, frame) -> icetray.I3Frame:
        """Save the frame to file at `self.cache_dir`.

        Record the file-saving in `self.state_dict` so it can't happen again.
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


def perform_scan(event_id_string, state_dict, cache_dir, port=5555, numclients=10, logger=simple_print_logger, skymap_plotting_callback=None, finish_function=None, RemoteSubmitPrefix=""):
    npos_per_pixel = 7
    pixel_overhead_percent = 100 # send 100% more pixels than we have actual capacity for
    parallel_pixels = int((float(numclients)/float(npos_per_pixel))*(1.+float(pixel_overhead_percent)/100.))
    if parallel_pixels <= 0: parallel_pixels = 1
    logger("The number of pixels to send out in parallel is {0} -> {1} jobs ({2}% more with {3} sub-scans per pixel) on {4} clients".format(parallel_pixels, parallel_pixels*npos_per_pixel, pixel_overhead_percent, npos_per_pixel, numclients))

    base_GCD_filename = state_dict['baseline_GCD_file']
    # print "base_GCD_path: {0}".format(config.GCD_base_dirs)
    # print "base_GCD_filename: {0}".format(base_GCD_filename)

    pixels_to_scan = PixelsToScan(
        state_dict=state_dict,
        InputTimeName="HESE_VHESelfVetoVertexTime",
        InputPosName="HESE_VHESelfVetoVertexPos",
        OutputParticleName="MillipedeSeedParticle",
        MaxPixelsInProcess=parallel_pixels,
        logger=logger,
        skymap_plotting_callback=skymap_plotting_callback,
        finish_function=finish_function,
    )
    find_best_reco_for_pixel = FindBestRecoResultForPixel()
    save_reco_results = SaveRecoResults(
        state_dict=state_dict,
        event_id=event_id_string,
        cache_dir=cache_dir
    )

    # TODO - be smarter about switching between send logic & recv logic (multi-thread?)

    # send pixels to client(s)
    while True:
        try:
            for frame in pixels_to_scan.do_process():
                print(f"<MOCK SEND FRAME TO CLIENT>: {frame}")  # TODO
        except NothingToSendException:
            break

    # receive back from client, collect & save
    for frame in [icetray.I3Frame()]*100:  # TODO - this will be the MQ stream
        print(f"<MOCK RECV FRAME FROM CLIENTS>: {frame}")  # TODO

        try:
            best_frame = find_best_reco_for_pixel.do_physics(frame)
        except WaitingForAllScansException:
            # this is okay, just waiting until we get everything
            print("We haven't received *all* the scans (frames) for a pixel yet...")
            continue

        out_frame = save_reco_results.do_physics(best_frame)
        # TODO - do we want to do anything with `out_frame`?

    # if this raises:
    #  then the MQ timeout is either too short or
    #  something catastrophic happened to a client
    find_best_reco_for_pixel.do_finish()

    return state_dict


def main() -> None:
    """Start up Server."""
    #import config
    #config.GCD_base_dirs = ["http://icecube:skua@convey.icecube.wisc.edu/data/exp/IceCube/2016/internal-system/PoleBaseGCDs"]

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("-p", "--port", action="store", type="int",
        default=5555, dest="PORT", help="The tcp port to use")
    parser.add_option("-n", "--numclients", action="store", type="int",
        default=10, dest="NUMCLIENTS", help="The number of clients to start")
    parser.add_option("-r", "--remote-submit-prefix", action="store", type="string",
        default="", dest="REMOTESUBMITPREFIX", help="The prefix to use in front of all condor commands")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exactly one event ID")
    eventID = args[0]

    RemoteSubmitPrefix = options.REMOTESUBMITPREFIX
    if RemoteSubmitPrefix is None: RemoteSubmitPrefix=""

    # get a file stager
    stagers = dataio.get_stagers()

    eventID, state_dict = load_cache_state(eventID, cache_dir=options.CACHEDIR, filestager=stagers)
    perform_scan(event_id_string=eventID, state_dict=state_dict, cache_dir=options.CACHEDIR, port=options.PORT, numclients=options.NUMCLIENTS, RemoteSubmitPrefix=RemoteSubmitPrefix)


if __name__ == "__main__":
    main()
