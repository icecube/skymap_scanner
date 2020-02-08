from __future__ import print_function
from __future__ import absolute_import

import os
import numpy
import tqdm
import healpy

import config

from I3Tray import *
from icecube import icetray, dataio, dataclasses
from icecube import VHESelfVeto
from icecube.frame_object_diff.segments import uncompress

from pulsar_icetray import ReceivePFrameWithMetadata, AcknowledgeReceivedPFrame, PulsarClientService, ReceiverService, SendPFrameWithMetadata

class WaitForNumberOfPFrames(icetray.I3Module):
    def __init__(self, ctx):
        super(WaitForNumberOfPFrames, self).__init__(ctx)
        self.AddParameter("SuspendAfterTheseNSides", "If set, wait until all of these nsides have been seen. Then exit", None)
        self.AddParameter("NPixelForNSide", "If set, a dict from nside to number of pixels to wait for", {})

        self.AddOutBox("OutBox")

    def Configure(self):
        suspend_after_these_nsides = self.GetParameter("SuspendAfterTheseNSides")
        if suspend_after_these_nsides is not None:
            self.nsides_to_process = set(suspend_after_these_nsides)
        else:
            self.nsides_to_process = None

        self.npixels_for_nside = self.GetParameter("NPixelForNSide")
        
        
        self.last_p_frame = None
        self.seen_all_frames = False

        self.data_for_nside = {}
        
        self.best_results = {}
        
        self.num_ignored_pixels = {}


    def report_progress(self):
        idxs = sorted(self.data_for_nside.keys())
        
        for idx in idxs:
            data = self.data_for_nside[idx]
            
            name = idx[0]
            nside = idx[1]
            
            if 'pbar' not in data:
                if nside in self.npixels_for_nside:
                    npix = self.npixels_for_nside[nside]
                else:
                    npix = 12 * (nside**2)
                data['pbar'] = tqdm.tqdm(smoothing=0.05, total=npix, desc='{} nside{}'.format(name,nside))
            if 'last_pixel_num_done' not in data:
                data['last_pixel_num_done'] = 0
            if 'pixelNumToFramesMap' not in data:
                data['pixelNumToFramesMap'] = {}
        
            pixel_num_done = len(data['pixelNumToFramesMap'])
            if pixel_num_done > data['last_pixel_num_done']:
                increment = pixel_num_done-data['last_pixel_num_done']
                data['last_pixel_num_done'] = pixel_num_done
                
                ignored_pixels = 0
                if (name, nside) in self.num_ignored_pixels:
                    data['pbar'].set_postfix(duplicate_pixels=self.num_ignored_pixels[(name, nside)], refresh=False)
                data['pbar'].update(increment)

    def Process(self):
        frame = self.PopFrame()
        if not frame:
            raise RuntimeError("WaitForNumberOfPFrames did not receive an input frame")
        
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
                if self.seen_all_frames:
                    raise RuntimeError("already received all frames. Received another one.")

                self.report_progress()
                
                # it's a physics frame. store it and return
                self.last_p_frame = frame
                return
            else:
                # it's some other frame and there is no previous P-frame.
                # Just push this one
                self.PushFrame(frame)
        

    def Work(self, p_frame, delimiter_frame):
        name  = p_frame["SCAN_EventName"].value
        nside = p_frame["SCAN_HealpixNSide"].value
        
        if nside in self.npixels_for_nside:
            npixel = self.npixels_for_nside[nside]
        else:
            npixel = 12 * (nside**2)
        pixel = p_frame["SCAN_HealpixPixel"].value

        if (name, nside) not in self.data_for_nside:
            self.data_for_nside[(name, nside)] = {'pixelNumToFramesMap': {}}
        data = self.data_for_nside[(name, nside)]

        pixelNumToFramesMap = data['pixelNumToFramesMap']

        if pixel in pixelNumToFramesMap:
            # print("**** Pixel {} has already been seen. Ignoring this copy!".format(pixel))
            if (name, nside) not in self.num_ignored_pixels:
                self.num_ignored_pixels[(name, nside)] = 1
            else:
                self.num_ignored_pixels[(name, nside)] += 1
            
            #self.PushFrame(p_frame) # p-frame -> do NOT push, eat this pixel
            self.PushFrame(delimiter_frame) # delimiter frame -> acknowledge this superfluous frame
            return

        # add the pixel to the cache map
        pixelNumToFramesMap[pixel] = (p_frame, delimiter_frame)


        if "MillipedeStarting2ndPass_millipedellh" in p_frame:
            thisLLH = p_frame["MillipedeStarting2ndPass_millipedellh"].logl
        else:
            thisLLH = numpy.nan

        if name not in self.best_results:
            self.best_results[name] = {'llh': thisLLH, 'frame': p_frame, 'nside': nside, 'pixel': pixel}

        if (thisLLH < self.best_results[name]['llh']) and (not numpy.isnan(thisLLH)):
            self.best_results[name] = {'llh': thisLLH, 'frame': p_frame, 'nside': nside, 'pixel': pixel}
        

        if len(pixelNumToFramesMap) >= npixel:
            self.report_progress()
            print("\nAll frames arrived for nside {}, pushing all {} frames.".format(nside, len(pixelNumToFramesMap)))
            
            for key in sorted(pixelNumToFramesMap.keys()):
                self.PushFrame(pixelNumToFramesMap[key][0]) # p-frame
                self.PushFrame(pixelNumToFramesMap[key][1]) # delimiter frame
                del pixelNumToFramesMap[key]

            del pixelNumToFramesMap
            if 'pbar' in data:
                data['pbar'].close()
            del self.data_for_nside[(name, nside)]
            
            if self.nsides_to_process is not None:
                if nside in self.nsides_to_process:
                    self.nsides_to_process.remove(nside)
            
                if len(self.data_for_nside) == 0:
                    # nothing more to process. Let's check if we are still expecting something, otherwise quit
                    
                    if len(self.nsides_to_process) == 0:
                        self.seen_all_frames = True
                        self.RequestSuspension()

    def Finish(self):
        if len(self.data_for_nside) > 0:
            print("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
            
            for name, nside in self.data_for_nside:
                if nside in self.npixels_for_nside:
                    npixel = self.npixels_for_nside[nside]
                else:
                    npixel = 12 * (nside**2)
                
                data = self.data_for_nside[(name, nside)]
                pixel_nums = set(data['pixelNumToFramesMap'].keys())
                all_pixel_nums = set(range(npixel))
                missing_pixels = sorted(list(all_pixel_nums.difference(pixel_nums)))
                
                print("  - {}:nside{} : missing pixels: {}".format(name, nside, missing_pixels))
                
            print("**** WARN ****  --  END")
        
        print("")
        print("Best pixels:")
        for name in self.best_results.keys():
            entry = self.best_results[name]
            
            minDec, minRA = healpy.pix2ang(entry['nside'], entry['pixel'])
            minDec = minDec - numpy.pi/2.

            print("  ** best entry for {:20} at (nside,pix)=({},{}) [llh={:.2f}]: dec={:.2f}deg RA={:.2f}deg / {:.2f}hours ".format(
                name, entry['nside'], entry['pixel'], entry['llh'],
                minDec*180./numpy.pi, minRA *180./numpy.pi, minRA*12./numpy.pi
                ))
        print("")

def get_reco_losses_inside(p_frame):
    if "MillipedeStarting2ndPass_totalRecoLossesInside" in p_frame:
        del p_frame["MillipedeStarting2ndPass_totalRecoLossesInside"]
    if "MillipedeStarting2ndPass_totalRecoLossesTotal" in p_frame:
        del p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"]
    
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




def save_pixels(broker, auth_token, topic_in, filename_out, nsides_to_wait_for, npixel_for_nside=None, delete_from_queue=True):
    if npixel_for_nside is None:
        npixel_for_nside = {}
    
    # connect to pulsar
    client_service = PulsarClientService(
        BrokerURL=broker,
        AuthToken=auth_token,
    )

    receiver_service = ReceiverService(
        client_service=client_service,
        topic=topic_in,
        subscription_name='skymap-saver-sub',
        force_single_consumer=True,
    )

    ########## the tray
    tray = I3Tray()

    tray.context['I3FileStager'] = dataio.get_stagers()

    tray.Add(ReceivePFrameWithMetadata, "ReceivePFrameWithMetadata",
        ReceiverService=receiver_service,
        )

    tray.Add(WaitForNumberOfPFrames, "WaitForNumberOfPFrames",
        SuspendAfterTheseNSides = nsides_to_wait_for,
        NPixelForNSide = npixel_for_nside)

    tray.Add(uncompress, "GCD_uncompress",
             keep_compressed=False,
             base_path=config.base_GCD_path)
    tray.AddModule(get_reco_losses_inside, "get_reco_losses_inside")
    
    tray.Add("I3Writer", "writer",
             Filename=filename_out,
             SkipKeys=['__msgid', '__msgtopic'],
             Streams=[
                   icetray.I3Frame.Geometry,
                   icetray.I3Frame.Calibration,
                   icetray.I3Frame.DetectorStatus,
                   icetray.I3Frame.DAQ,
                   icetray.I3Frame.Stream('p'),
                   icetray.I3Frame.Physics
                 ]
             )
    
    if delete_from_queue:
        # only acknowledge receipt (i.e. delete from the queue) if requested
        tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
            ReceiverService=receiver_service
            )

    tray.Execute()
    del tray
    
    del receiver_service
