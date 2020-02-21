from __future__ import print_function
from __future__ import absolute_import

import numpy
import healpy
import os
import random

import time

from icecube import icetray, dataclasses
from icecube import gulliver, millipede
from icecube import astro
from icecube import VHESelfVeto
from icecube import frame_object_diff
from icecube.frame_object_diff.segments import uncompress
from I3Tray import *

import config

from utils import get_event_mjd
#from scan_pixel_distributed import scan_pixel_distributed_server

class SendPixelsToScan(icetray.I3Module):
    def __init__(self, ctx):
        super(SendPixelsToScan, self).__init__(ctx)
        self.AddParameter("FramePacket", "The GCDQp frame packet to send", None)
        self.AddParameter("NSide", "The healpix resolution in terms of \"nside\".", 8)
        self.AddParameter("InputTimeName", "Name of an I3Double to use as the vertex time for the coarsest scan", "HESE_VHESelfVetoVertexTime")
        self.AddParameter("InputPosName", "Name of an I3Position to use as the vertex position for the coarsest scan", "HESE_VHESelfVetoVertexPos")
        self.AddParameter("OutputParticleName", "Name of the output I3Particle", "MillipedeSeedParticle")
        self.AddOutBox("OutBox")

    def Configure(self):
        self.GCDQpFrames = self.GetParameter("FramePacket")
        self.nside = self.GetParameter("NSide")
        self.input_pos_name = self.GetParameter("InputPosName")
        self.input_time_name = self.GetParameter("InputTimeName")
        self.output_particle_name = self.GetParameter("OutputParticleName")

        p_frame = self.GCDQpFrames[-1]
        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.seed_position = p_frame[self.input_pos_name]
        self.seed_time = p_frame[self.input_time_name].value
        self.seed_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_mjd = get_event_mjd(self.GCDQpFrames)

        self.pixels_to_push = range(healpy.nside2npix(self.nside))

    def Process(self):
        # driving module - we will be called repeatedly by IceTray with no input frames
        if self.PopFrame():
            raise RuntimeError("SendPixelsToScan needs to be used as a driving module")

        # push GCDQp packet if not done so already
        if self.GCDQpFrames:
            for frame in self.GCDQpFrames:
                self.PushFrame(frame)
            self.GCDQpFrames = None
            print("Commencing full-sky scan. I will first need to start up the condor jobs, this might take a while...".format())
            return

        # submit one more pixel
        if len(self.pixels_to_push) > 0:
            # get the first item from the list and remove it from the list
            next_pixel = self.pixels_to_push.pop(0)
            
            # create and push a P-frame to be processed
            self.CreatePFrame(nside=self.nside, pixel=next_pixel)
        else:
            # we are done.
            self.RequestSuspension()

    def CreatePFrame(self, nside, pixel):
        dec, ra = healpy.pix2ang(nside, pixel)
        dec = numpy.pi/2. - dec
        zenith, azimuth = astro.equa_to_dir(ra, dec, self.event_mjd)
        zenith = float(zenith)
        azimuth = float(azimuth)
        direction = dataclasses.I3Direction(zenith,azimuth)

        position = self.seed_position
        time = self.seed_time
        energy = self.seed_energy

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

            thisPosition = dataclasses.I3Position(position.x + posVariation.x, position.y + posVariation.y, position.z + posVariation.z)

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
            # print("all scans arrived for pixel", index)
            bestFrame = None
            bestFrameLLH = None
            for frame in self.pixelNumToFramesMap[index]:
                if "MillipedeStarting2ndPass_millipedellh" in frame:
                    thisLLH = frame["MillipedeStarting2ndPass_millipedellh"].logl
                else:
                    thisLLH = numpy.nan
                # print("  * llh =", thisLLH)
                if (bestFrame is None) or ((thisLLH < bestFrameLLH) and (not numpy.isnan(thisLLH))):
                    bestFrame=frame
                    bestFrameLLH=thisLLH

            # print("all scans arrived for pixel", index, "best LLH is", bestFrameLLH)

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
        print(self.pixelNumToFramesMap)
        print("**** WARN ****  --  END")


def get_reco_losses_inside(p_frame):
    if "MillipedeStarting2ndPass" not in p_frame:
        p_frame["MillipedeStarting2ndPass_totalRecoLossesInside"] = dataclasses.I3Double(numpy.nan)
        p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(numpy.nan)
        return
    recoParticle = p_frame["MillipedeStarting2ndPass"]

    if "MillipedeStarting2ndPassParams" not in p_frame:
        p_frame["MillipedeStarting2ndPass_totalRecoLossesInside"] = dataclasses.I3Double(numpy.nan)
        p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(numpy.nan)
        return

    def getRecoLosses(vecParticles):
        losses = []
        for p in vecParticles:
            if not p.is_cascade: continue
            if p.energy==0.: continue
            losses.append([p.time, p.energy])
        return losses
    recoLosses = getRecoLosses(p_frame["MillipedeStarting2ndPassParams"])

    intersectionPoints = VHESelfVeto.IntersectionsWithInstrumentedVolume(p_frame["I3Geometry"], recoParticle)
    intersectionTimes = []
    for intersectionPoint in intersectionPoints:
        vecX = intersectionPoint.x - recoParticle.pos.x
        vecY = intersectionPoint.y - recoParticle.pos.y
        vecZ = intersectionPoint.z - recoParticle.pos.z

        prod = vecX*recoParticle.dir.x + vecY*recoParticle.dir.y + vecZ*recoParticle.dir.z
        dist = numpy.sqrt(vecX**2 + vecY**2 + vecZ**2)
        if prod < 0.: dist *= -1.
        intersectionTimes.append(dist/dataclasses.I3Constants.c + recoParticle.time)

    entryTime = None
    exitTime = None
    intersectionTimes = sorted(intersectionTimes)
    if len(intersectionTimes)==0:
        p_frame["MillipedeStarting2ndPass_totalRecoLossesInside"] = dataclasses.I3Double(0.)

        totalRecoLosses = 0.
        for entry in recoLosses:
            totalRecoLosses += entry[1]
        p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(totalRecoLosses)
        return

    entryTime = intersectionTimes[0]-60.*I3Units.m/dataclasses.I3Constants.c
    intersectionTimes = intersectionTimes[1:]
    exitTime = intersectionTimes[-1]+60.*I3Units.m/dataclasses.I3Constants.c
    intersectionTimes = intersectionTimes[:-1]

    totalRecoLosses = 0.
    totalRecoLossesInside = 0.
    for entry in recoLosses:
        totalRecoLosses += entry[1]
        if entryTime is not None and entry[0] < entryTime: continue
        if exitTime  is not None and entry[0] > exitTime:  continue
        totalRecoLossesInside += entry[1]

    p_frame["MillipedeStarting2ndPass_totalRecoLossesInside"] = dataclasses.I3Double(totalRecoLossesInside)
    p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(totalRecoLosses)


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

        # compute and retrieve losses
        get_reco_losses_inside(frame)
        recoLossesInside = frame["MillipedeStarting2ndPass_totalRecoLossesInside"].value
        recoLossesTotal = frame["MillipedeStarting2ndPass_totalRecoLossesTotal"].value

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

        # print(" - saving pixel file {0}...".format(pixel_file_name))
        save_GCD_frame_packet_to_file([frame], pixel_file_name)

        self.PushFrame(frame)


def perform_scan(event_id_string, state_dict, cache_dir, base_GCD_path, port=5555, logger=simple_print_logger, skymap_plotting_callback=None):
    numclients = 1000 # an approximation...

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
        skymap_plotting_callback=skymap_plotting_callback
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
    tray.AddSegment(scan_pixel_distributed_server, "scan_pixel_distributed",
        port=port
    )

    #### collect the results
    tray.AddModule(FindBestRecoResultForPixel, "FindBestRecoResultForPixel")

    # the next module needs the geometry...
    tray.Add(uncompress, "GCD_uncompress",
             keep_compressed=True,
             base_path=base_GCD_path)
    tray.AddModule(CollectRecoResults, "CollectRecoResults",
        state_dict = state_dict,
        event_id = event_id_string,
        cache_dir = cache_dir
    )

    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray

    return state_dict
