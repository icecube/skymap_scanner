import numpy
import healpy
import os
import random

import time

from icecube import icetray, dataclasses
from icecube import gulliver, millipede
from I3Tray import *

from utils import parse_event_id

from choose_new_pixels_to_scan import choose_new_pixels_to_scan
from utils import save_GCD_frame_packet_to_file
from traysegments import scan_pixel_distributed

class SendPixelsToScan(icetray.I3Module):
    def __init__(self, ctx):
        super(SendPixelsToScan, self).__init__(ctx)
        self.AddParameter("state_dict", "The state_dict", None)
        self.AddParameter("InputTimeName", "Name of an I3Double to use as the vertex time for the coarsest scan", "HESE_VHESelfVetoVertexTime")
        self.AddParameter("InputPosName", "Name of an I3Position to use as the vertex position for the coarsest scan", "HESE_VHESelfVetoVertexPos")
        self.AddParameter("OutputParticleName", "Name of the output I3Particle", "MillipedeSeedParticle")
        self.AddParameter("MaxPixelsInProcess", "Do not submit more pixels than this to the downstream module", 1000)
        self.AddOutBox("OutBox")
        
    def Configure(self):
        self.state_dict = self.GetParameter("state_dict")
        self.input_pos_name = self.GetParameter("InputPosName")
        self.input_time_name = self.GetParameter("InputTimeName")
        self.output_particle_name = self.GetParameter("OutputParticleName")
        self.max_pixels_in_process = self.GetParameter("MaxPixelsInProcess")
        
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

        self.pixels_in_process = set()


    def Process(self):
        # driving module - we will be called repeatedly by IceTray with no input frames
        if self.PopFrame():
            raise RuntimeError("SendPixelsToScan needs to be used as a driving module")

        # push GCDQp packet if not done so already
        if self.GCDQpFrames:
            for frame in self.GCDQpFrames:
                self.PushFrame(frame)
            self.GCDQpFrames = None
            return

        # see if we think we are processing pixels but they have finished since
        for nside in self.state_dict["nsides"]:
            for pixel in self.state_dict["nsides"][nside]:
                if (nside,pixel) in self.pixels_in_process:
                    self.pixels_in_process.remove( (nside,pixel) )

        # find pixels to refine
        pixels_to_refine = choose_new_pixels_to_scan(self.state_dict)
        
        if len(pixels_to_refine) == 0:
            print "** there are no pixels left to refine. stopping."
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
        print "Scanning nside={0}, pixel={1}".format(nside,pixel)

        zenith, azimuth = healpy.pix2ang(nside, pixel)
        direction = dataclasses.I3Direction(zenith,azimuth)

        if nside == 8:
            position = self.fallback_position
            time = self.fallback_time
            energy = self.fallback_energy
        else:
            coarser_nside = nside
            while True:
                coarser_nside = coarser_nside/2
                coarser_pixel = healpy.ang2pix(coarser_nside, zenith, azimuth)
                
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
            eventHeader.sub_event_id = pixel
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

            print "all scans arrived for pixel", index, "best LLH is", bestFrameLLH

            if bestFrame is None:
                # just push the first frame if all of them are nan
                self.PushFrame(self.pixelNumToFramesMap[index][0])
            else:
                self.PushFrame(bestFrame)

            del self.pixelNumToFramesMap[index]

    def Finish(self):
        if len(self.pixelNumToFramesMap) == 0:
            return

        print "**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete"
        print self.pixelNumToFramesMap
        print "**** WARN ****  --  END"


        
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
            raise RuntimeError("\"MillipedeStarting2ndPass_millipedellh\" not found in reconstructed frame")
            
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

        print " - saving pixel file {0}...".format(pixel_file_name)
        save_GCD_frame_packet_to_file([frame], pixel_file_name)
            
        self.PushFrame(frame)


def perform_scan(event_id_string, state_dict, cache_dir, port=5555, numclients=10):
    npos_per_pixel = 7
    pixel_overhead_percent = 50 # send 50% more pixels than we have actual capacity for
    parallel_pixels = int((float(numclients)/float(npos_per_pixel))*(1.+float(pixel_overhead_percent)/100.))
    if parallel_pixels <= 0: parallel_pixels = 1
    print "number of pixels to send out in parallel {0} -> {1} jobs".format(parallel_pixels, parallel_pixels*npos_per_pixel)

    base_GCD_path, base_GCD_filename = os.path.split(state_dict['baseline_GCD_file'])
    print "base_GCD_path: {0}".format(base_GCD_path)
    print "base_GCD_filename: {0}".format(base_GCD_filename)
    
    ExcludedDOMs = [
        'CalibrationErrata',
        'BadDomsList',
        'DeepCoreDOMs',
        'SaturatedDOMs',
        'BrightDOMs',
        'SplitUncleanedInIcePulsesLatePulseCleanedTimeWindows',
        ]
    
    tray = I3Tray()

    tray.AddModule(SendPixelsToScan, "SendPixelsToScan",
        state_dict=state_dict,
        InputTimeName="HESE_VHESelfVetoVertexTime",
        InputPosName="HESE_VHESelfVetoVertexPos",
        OutputParticleName="MillipedeSeedParticle",
        MaxPixelsInProcess=parallel_pixels
    )

    # #### do the scan
    # def FakeScan(frame):
    #     fp = millipede.MillipedeFitParams()
    #     fp.logl = random.uniform(100.,200.)
    #     frame["MillipedeStarting2ndPass_millipedellh"] = fp
    #     
    #     p = dataclasses.I3Particle(frame["MillipedeSeedParticle"])
    #     frame["MillipedeStarting2ndPass"] = p
    #     
    #     time.sleep(0.002)
    # tray.AddModule(FakeScan)

    #### do the scan
    tray.AddSegment(scan_pixel_distributed, "scan_pixel_distributed",
        port=port,
        ExcludedDOMs=ExcludedDOMs,
        NumClients=numclients,
        base_GCD_path=base_GCD_path,
        base_GCD_filename=base_GCD_filename,
    )
        
    #### collect the results
    tray.AddModule(FindBestRecoResultForPixel, "FindBestRecoResultForPixel")
    tray.AddModule(CollectRecoResults, "CollectRecoResults",
        state_dict = state_dict,
        event_id = event_id_string,
        cache_dir = cache_dir
    )

    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray


if __name__ == "__main__":
    from optparse import OptionParser
    from load_scan_state import load_cache_state

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("-p", "--port", action="store", type="int",
        default=5555, dest="PORT", help="The tcp port to use")
    parser.add_option("-n", "--numclients", action="store", type="int",
        default=10, dest="NUMCLIENTS", help="The number of clients to start")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    eventID, state_dict = load_cache_state(eventID, cache_dir=options.CACHEDIR)
    perform_scan(event_id_string=eventID, state_dict=state_dict, cache_dir=options.CACHEDIR, port=options.PORT, numclients=options.NUMCLIENTS)
