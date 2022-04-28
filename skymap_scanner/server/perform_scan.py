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

import os
import time
from optparse import OptionParser

import healpy  # type: ignore[import]
import numpy
from I3Tray import I3Tray, I3Units  # type: ignore[import]
from icecube import astro, dataclasses, dataio, icetray  # type: ignore[import]

from ..mq_tools.pulsar_icetray import (
    AcknowledgeReceivedPFrame,
    PulsarClientService,
    ReceivePFrame,
    ReceiverService,
    SendPFrame,
)
from .choose_new_pixels_to_scan import choose_new_pixels_to_scan
from .load_scan_state import load_cache_state
from .utils import get_event_mjd, save_GCD_frame_packet_to_file


def simple_print_logger(text):
    print(text)


class SendPixelsToScan(icetray.I3Module):
    def __init__(self, ctx):
        super(SendPixelsToScan, self).__init__(ctx)
        self.AddParameter("state_dict", "The state_dict", None)
        self.AddParameter("InputTimeName", "Name of an I3Double to use as the vertex time for the coarsest scan", "HESE_VHESelfVetoVertexTime")
        self.AddParameter("InputPosName", "Name of an I3Position to use as the vertex position for the coarsest scan", "HESE_VHESelfVetoVertexPos")
        self.AddParameter("OutputParticleName", "Name of the output I3Particle", "MillipedeSeedParticle")
        self.AddParameter("MaxPixelsInProcess", "Do not submit more pixels than this to the downstream module", 1000)
        self.AddParameter("logger", "a callback function for semi-verbose logging", simple_print_logger)
        self.AddParameter("logging_interval_in_seconds", "call the logger callback with this interval", 5*60)
        self.AddParameter("skymap_plotting_callback", "a callback function the receives the full current state of the map", None)
        self.AddParameter("skymap_plotting_callback_interval_in_seconds", "a callback function the receives the full ", 30*60)
        self.AddParameter("finish_function", "function to be run once scan is finished. handles final plotting.", None)
        self.AddOutBox("OutBox")

    def Configure(self):
        self.state_dict = self.GetParameter("state_dict")
        self.input_pos_name = self.GetParameter("InputPosName")
        self.input_time_name = self.GetParameter("InputTimeName")
        self.output_particle_name = self.GetParameter("OutputParticleName")
        self.max_pixels_in_process = self.GetParameter("MaxPixelsInProcess")
        self.logger = self.GetParameter("logger")
        self.logging_interval_in_seconds = self.GetParameter("logging_interval_in_seconds")
        self.skymap_plotting_callback = self.GetParameter("skymap_plotting_callback")
        self.skymap_plotting_callback_interval_in_seconds = self.GetParameter("skymap_plotting_callback_interval_in_seconds")
        self.finish_function = self.GetParameter("finish_function")

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

    def Process(self):
        # driving module - we will be called repeatedly by IceTray with no input frames
        if self.PopFrame():
            raise RuntimeError("SendPixelsToScan needs to be used as a driving module")

        # push GCDQp packet if not done so already
        if self.GCDQpFrames:
            for frame in self.GCDQpFrames:
                self.PushFrame(frame)
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

            self.RequestSuspension()
            return

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
            self.CreatePFrame(nside=nside_pix[0], pixel=nside_pix[1])
            something_was_submitted = True

        if not something_was_submitted:
            # there are submitted pixels left that haven't yet arrived

            # print "** all pixels are processing. waiting one second..."
            time.sleep(1)

            # send a special frame type to I3Distribute in order to flush its
            # output queue
            self.PushFrame( icetray.I3Frame( icetray.I3Frame.Stream('\x05') ) )

    def CreatePFrame(self, nside, pixel):
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

            self.PushFrame(p_frame)


class FindBestRecoResultForPixel(icetray.I3Module):
    def __init__(self, ctx):
        super(FindBestRecoResultForPixel, self).__init__(ctx)
        self.AddOutBox("OutBox")
        self.AddParameter("NPosVar", "Number of position variations to collect", 7)

    def Configure(self):
        self.NPosVar = self.GetParameter("NPosVar")

        self.pixelNumToFramesMap = {}

    def Physics(self, frame):
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
                self.PushFrame(self.pixelNumToFramesMap[index][0])
            else:
                self.PushFrame(bestFrame)

            del self.pixelNumToFramesMap[index]

    def Finish(self):
        if len(self.pixelNumToFramesMap) == 0:
            return

        print("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
        print((self.pixelNumToFramesMap))
        print("**** WARN ****  --  END")


class CollectRecoResults(icetray.I3Module):
    def __init__(self, ctx):
        super(CollectRecoResults, self).__init__(ctx)
        self.AddParameter("state_dict", "The state_dict", None)
        self.AddParameter("event_id", "The event_id", None)
        self.AddParameter("cache_dir", "The cache_dir", None)
        self.AddOutBox("OutBox")

    def Configure(self):
        self.state_dict = self.GetParameter("state_dict")
        self.event_id = self.GetParameter("event_id")
        self.cache_dir = self.GetParameter("cache_dir")

        self.this_event_cache_dir = os.path.join(self.cache_dir, self.event_id)

    def Physics(self, frame):
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

        self.PushFrame(frame)


def send_scan_icetray(
    event_id_string,
    state_dict,
    cache_dir,
    broker,  # for pulsar
    auth_token,  # for pulsar
    topic_to_clients,  # for pulsar
    producer_name,  # for pulsar
    numclients=10,
    logger=simple_print_logger,
    skymap_plotting_callback=None,
    finish_function=None,
):
    """Send Pixels to be scanned by client(s)

    Based on:
        python/perform_scan.py
        cloud_tools/send_scan.py
    """
    npos_per_pixel = 7
    pixel_overhead_percent = 100 # send 100% more pixels than we have actual capacity for
    parallel_pixels = int((float(numclients)/float(npos_per_pixel))*(1.+float(pixel_overhead_percent)/100.))
    if parallel_pixels <= 0: parallel_pixels = 1
    logger("The number of pixels to send out in parallel is {0} -> {1} jobs ({2}% more with {3} sub-scans per pixel) on {4} workers".format(parallel_pixels, parallel_pixels*npos_per_pixel, pixel_overhead_percent, npos_per_pixel, numclients))

    tray = I3Tray()

    tray.AddModule(SendPixelsToScan, "SendPixelsToScan",
        state_dict=state_dict,
        InputTimeName="HESE_VHESelfVetoVertexTime",
        InputPosName="HESE_VHESelfVetoVertexPos",
        OutputParticleName="MillipedeSeedParticle",
        MaxPixelsInProcess=parallel_pixels,
        logger=logger,
        skymap_plotting_callback=skymap_plotting_callback,
        finish_function=finish_function,
    )

    def makeSurePulsesExist(frame, pulsesName):
        if pulsesName not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName+"TimeWindows" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeWindows"))
        if pulsesName+"TimeRange" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeRange"))
    tray.AddModule(makeSurePulsesExist, "makeSurePulsesExist", pulsesName="SplitUncleanedInIcePulsesLatePulseCleaned")

    client_service = PulsarClientService(
        BrokerURL=broker,
        AuthToken=auth_token
    )

    # now send all P-frames as pulsar messages
    tray.Add(SendPFrame, "SendPFrame",
        ClientService=client_service,
        Topic=topic_to_clients,
        ProducerName=producer_name,
        I3IntForSequenceID="SCAN_EventOverallIndex",
        PartitionKey=lambda frame: frame["SCAN_EventName"].value + '_' + str(frame["SCAN_HealpixNSide"].value) + '_' + str(frame["SCAN_HealpixPixel"].value)
    )

    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray
    del client_service

    return state_dict


def collect_and_save_pixels_icetray(
    broker,
    auth_token,
    topic_from_clients,
    event_id_string,
    state_dict,
    cache_dir,
):
    """Collect pixel scans from MQ and save to disk.

    Based on:
        python/perform_scan.py
        cloud_tools/collect_pixels.py
        cloud_tools/save_pixels.py (only nominally)
    """
    # connect to pulsar
    client_service = PulsarClientService(
        BrokerURL=broker,
        AuthToken=auth_token,
    )

    receiver_service = ReceiverService(
        client_service=client_service,
        topic=topic_from_clients,
        subscription_name='skymap-collector-sub',
        force_single_consumer=True,
    )

    ########## the tray
    tray = I3Tray()

    tray.Add(ReceivePFrame, "ReceivePFrame",
        ReceiverService=receiver_service,
        MaxCacheEntriesPerFrameStop=100, # cache more (so we do not have to re-connect in case we are collecting many different events)
        )

    tray.Add(FindBestRecoResultForPixel, "FindBestRecoResultForPixel")

    tray.AddModule(CollectRecoResults, "CollectRecoResults",
        state_dict = state_dict,
        event_id = event_id_string,
        cache_dir = cache_dir
    )

    tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
        ReceiverService=receiver_service
        )

    tray.Execute()
    del tray

    del receiver_service
    del client_service


def main():

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("-n", "--numclients", action="store", type="int",  # TODO - remove
        default=10, dest="NUMCLIENTS", help="The number of clients to start")
    parser.add_option("-t", "--topic_to_clients", action="store", type="string",
        default="persistent://icecube/skymap/to_be_scanned",
        dest="TOPIC_TO_CLIENTS", help="The Pulsar topic name for pixels to be scanned")
    parser.add_option("-s", "--topic_from_clients", action="store", type="string",
        default="persistent://icecube/skymap/scanned",
        dest="TOPIC_FROM_CLIENTS", help="The Pulsar topic name for pixels that have been scanned")
    parser.add_option("-b", "--broker", action="store", type="string",
        default="pulsar://localhost:6650",
        dest="BROKER", help="The Pulsar broker URL to connect to")
    parser.add_option("-a", "--auth-token", action="store", type="string",
        default=None,
        dest="AUTH_TOKEN", help="The Pulsar authentication token to use")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exactly one event ID")
    eventID = args[0]

    # get a file stager
    stagers = dataio.get_stagers()

    eventID, state_dict = load_cache_state(eventID, cache_dir=options.CACHEDIR, filestager=stagers)
    state_dict = send_scan_icetray(
        event_id_string=eventID,
        state_dict=state_dict,
        cache_dir=options.CACHEDIR,
        numclients=options.NUMCLIENTS,
        broker=options.BROKER,
        auth_token=options.AUTH_TOKEN,
        topic_to_clients=options.TOPIC_TO_CLIENTS,
        producer_name="TEST-PRODUCER_NAME",  # TODO - probably includes event name (nside? area_center_nside? area_center_pixel?)
    )
    collect_and_save_pixels_icetray(
        broker=options.BROKER,
        auth_token=options.AUTH_TOKEN,
        topic_from_clients=options.TOPIC_FROM_CLIENTS,
        event_id_string=eventID,
        state_dict=state_dict,
        cache_dir=options.CACHEDIR,
    )


if __name__ == "__main__":
    main()
