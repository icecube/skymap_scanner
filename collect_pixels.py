from __future__ import print_function
from __future__ import absolute_import

import os
import time
import numpy

import config

from I3Tray import *
from icecube import icetray, dataio, dataclasses
from icecube import VHESelfVeto
from icecube.frame_object_diff.segments import uncompress

from pulsar_icetray import ReceivePFrameWithMetadata, AcknowledgeReceivedPFrame, ReceiverService, SendPFrameWithMetadata

class FindBestRecoResultForPixel(icetray.I3Module):
    def __init__(self, ctx):
        super(FindBestRecoResultForPixel, self).__init__(ctx)
        self.AddOutBox("OutBox")
        self.AddParameter("NPosVar", "Number of position variations to collect", 7)

    def Configure(self):
        self.NPosVar = self.GetParameter("NPosVar")

        self.pixelNumToFramesMap = {}
        self.last_p_frame = None

    def Process(self):
        frame = self.PopFrame()
        if not frame:
            raise RuntimeError("FindBestRecoResultForPixel did not receive an input frame")
        
        # assume we always receive exactly one P frame and one "packet end" frame
        if self.last_p_frame is not None:
            # we received a P-frame last. It *has* to be a "packet-end" frame now
            if frame.Stop != icetray.I3Frame.Stream('\03'):
                raise RuntimeError("received packets must be [P][\\03]. Received [P][{}] instead".format(frame.Stop))
            
            # now do the actual work
            self.Work(self.last_p_frame, frame)
            
            # re-set
            self.last_p_frame = None
        else: # previous frame was not a P-frame
            if frame.Stop == icetray.I3Frame.Physics:
                # it's a physics frame. store it and return
                self.last_p_frame = frame
                return
            else:
                # it's some other frame and there is no previous P-frame.
                # Just push this one
                self.PushFrame(frame)
        

    def Work(self, p_frame, delimiter_frame):
        if "SCAN_HealpixNSide" not in p_frame:
            raise RuntimeError("SCAN_HealpixNSide not in frame")
        if "SCAN_HealpixPixel" not in p_frame:
            raise RuntimeError("SCAN_HealpixPixel not in frame")
        if "SCAN_PositionVariationIndex" not in p_frame:
            raise RuntimeError("SCAN_PositionVariationIndex not in frame")

        nside = p_frame["SCAN_HealpixNSide"].value
        pixel = p_frame["SCAN_HealpixPixel"].value
        index = (nside,pixel)
        posVarIndex = p_frame["SCAN_PositionVariationIndex"].value

        if index not in self.pixelNumToFramesMap:
            self.pixelNumToFramesMap[index] = []
        self.pixelNumToFramesMap[index].append( (p_frame, delimiter_frame) )

        if len(self.pixelNumToFramesMap[index]) >= self.NPosVar:
            # print("all scans arrived for pixel", index)
            bestItemIndex = None
            bestFrameLLH = None
            for i, item in enumerate(self.pixelNumToFramesMap[index]):
                frame = item[0]
                if "MillipedeStarting2ndPass_millipedellh" in frame:
                    thisLLH = frame["MillipedeStarting2ndPass_millipedellh"].logl
                else:
                    thisLLH = numpy.nan
                # print("  * llh =", thisLLH)
                if (bestItemIndex is None) or ((thisLLH < bestFrameLLH) and (not numpy.isnan(thisLLH))):
                    bestItemIndex=i
                    bestFrameLLH=thisLLH

            print("all scans arrived for pixel {}, best LLH is {} in frame index {}".format(index, bestFrameLLH, bestItemIndex))

            if bestItemIndex is None:
                # just use the first frame if all of them are nan
                bestItemIndex = 0

            # now push all delimiter frames but only the P-frame we deemed best
            for i, item in enumerate(self.pixelNumToFramesMap[index]):
                if i == bestItemIndex:
                    self.PushFrame(self.pixelNumToFramesMap[index][i][0])
                self.PushFrame(self.pixelNumToFramesMap[index][i][1])

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


def collect_pixels(broker, topic_in, topic_out):
    receiver_service = ReceiverService(
        broker_url=broker,
        topic=topic_in,
        subscription_name='skymap-collector-sub',
        force_single_consumer=True,
    )

    ########## the tray
    tray = I3Tray()

    tray.Add(ReceivePFrameWithMetadata, "ReceivePFrameWithMetadata",
        ReceiverService=receiver_service,
        )

    # def notify(frame):
    #     print("MillipedeStarting2ndPass", frame["MillipedeStarting2ndPass"])
    #     #time.sleep(3)
    # tray.AddModule(notify, "notify")

    tray.Add(FindBestRecoResultForPixel, "FindBestRecoResultForPixel")

    tray.Add(uncompress, "GCD_uncompress",
             keep_compressed=True,
             base_path=config.base_GCD_path)
    tray.AddModule(get_reco_losses_inside, "get_reco_losses_inside")
    
    ##### TODO: this is where you would do something with the LLH result for this particular pixel
    ##### e.g. send it to another queue, or just write it out using an I3Writer.
    
    # tray.Add(SendPFrameWithMetadata, "SendPFrameWithMetadata",
    #     BrokerURL=broker,
    #     Topic=topic_out,
    #     MetadataTopic=None, # no specific metadata topic, will be dynamic according to incoming frame tags
    #     )
    
    tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
        ReceiverService=receiver_service
        )

    tray.Execute()
    del tray
    
    del receiver_service
