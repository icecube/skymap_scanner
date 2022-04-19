"""The Producer service."""

# fmt: off
# pylint: skip-file


import time
from optparse import OptionParser

import healpy
import numpy
from I3Tray import I3Units
from icecube import astro, dataclasses, dataio, icetray

from .choose_new_pixels_to_scan import choose_new_pixels_to_scan
from .load_scan_state import load_cache_state
from .utils import get_event_mjd


def simple_print_logger(text):
    print(text)


class NothingToSendException(Exception):
    """Raise this when there is nothing (more) to send."""


class SendPixelsToScan:
    """Manage sending pixels to worker clients for processing."""

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

    def send_to_worker(self, frame):
        """Send frame to worker client."""
        # TODO
        print(f"<MOCK SEND TO WORKER>: {frame}")

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

    def process_and_send(self):
        """Process the GCDQpFrames & PFrames, and send each to worker client(s)."""

        # push GCDQp packet if not done so already
        if self.GCDQpFrames:
            for frame in self.GCDQpFrames:
                self.send_to_worker(frame)
            self.GCDQpFrames = None
            self.logger("Commencing full-sky scan. I will first need to start up the condor jobs, this might take a while...".format())
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

            # self.RequestSuspension()  # TODO - replace with some stopping signal
            raise NothingToSendException()
            # return

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
            self.create_then_send_pframe(nside=nside_pix[0], pixel=nside_pix[1])
            something_was_submitted = True

        if not something_was_submitted:
            # there are submitted pixels left that haven't yet arrived

            # print "** all pixels are processing. waiting one second..."
            time.sleep(1)

            # send a special frame type to I3Distribute in order to flush its
            # output queue
            self.send_to_worker( icetray.I3Frame( icetray.I3Frame.Stream('\x05') ) )

    def create_then_send_pframe(self, nside, pixel):
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

            self.send_to_worker(p_frame)


def perform_scan(event_id_string, state_dict, cache_dir, port=5555, numclients=10, logger=simple_print_logger, skymap_plotting_callback=None, finish_function=None, RemoteSubmitPrefix=""):
    npos_per_pixel = 7
    pixel_overhead_percent = 100 # send 100% more pixels than we have actual capacity for
    parallel_pixels = int((float(numclients)/float(npos_per_pixel))*(1.+float(pixel_overhead_percent)/100.))
    if parallel_pixels <= 0: parallel_pixels = 1
    logger("The number of pixels to send out in parallel is {0} -> {1} jobs ({2}% more with {3} sub-scans per pixel) on {4} workers".format(parallel_pixels, parallel_pixels*npos_per_pixel, pixel_overhead_percent, npos_per_pixel, numclients))

    base_GCD_filename = state_dict['baseline_GCD_file']
    # print "base_GCD_path: {0}".format(config.GCD_base_dirs)
    # print "base_GCD_filename: {0}".format(base_GCD_filename)

    sender = SendPixelsToScan(
        state_dict=state_dict,
        InputTimeName="HESE_VHESelfVetoVertexTime",
        InputPosName="HESE_VHESelfVetoVertexPos",
        OutputParticleName="MillipedeSeedParticle",
        MaxPixelsInProcess=parallel_pixels,
        logger=logger,
        skymap_plotting_callback=skymap_plotting_callback,
        finish_function=finish_function,
    )

    while True:
        try:
            sender.process_and_send()
        except NothingToSendException:
            break

    return state_dict


def main() -> None:
    """Start up Producer service."""
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
