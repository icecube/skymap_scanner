from __future__ import print_function
from __future__ import absolute_import

import os
import time
import numpy
import copy

import tqdm

import config

from I3Tray import *
from icecube import icetray, dataio, dataclasses
from icecube import VHESelfVeto
from icecube.frame_object_diff.segments import uncompress

from pulsar_icetray import ReceivePFrameWithMetadata, AcknowledgeReceivedPFrame, PulsarClientService, ReceiverService, SendPFrameWithMetadata

def memory_usage_psutil():
    # return the memory usage in MB
    import psutil
    process = psutil.Process(os.getpid())
    mem = process.memory_info()[0] / float(2 ** 20)
    return mem
    
class FindBestRecoResultForPixel(icetray.I3Module):
    def __init__(self, ctx):
        super(FindBestRecoResultForPixel, self).__init__(ctx)
        self.AddOutBox("OutBox")
        self.AddParameter("NPosVar", "Number of position variations to collect", 7)

    def Configure(self):
        self.NPosVar = self.GetParameter("NPosVar")

        self.pixelNumToFramesMap = {}
        self.last_p_frame = None
        
        self.cache_size = 0
        
        self.current_metadata = []
        
    def update_current_metadata(self, frame, clean_metadata_frame=True):
        stop_id = frame.Stop.id
        
        pos_to_use = None
        
        for i in range(len(self.current_metadata)):
            entry = self.current_metadata[i]
            if entry[0] == stop_id:
                pos_to_use = i
                break
        if pos_to_use is None:
            self.current_metadata.append( (stop_id, None) )
            pos_to_use = len(self.current_metadata)-1
        
        frame_copy = copy.copy(frame)
        del frame
        frame_copy.purge()
        
        if clean_metadata_frame:
            # clean everything but the message topic reference
            for key in frame_copy.keys():
                if key == '__msgtopic': continue
                del frame_copy[key]
        
        self.current_metadata[pos_to_use] = (stop_id, frame_copy)

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
            elif frame.Stop == icetray.I3Frame.Stream('\03'):
                print(" ***** superfluous packet end frame encountered. Pushing and ignoring.")
                self.PushFrame(frame)
            else:
                # it's a metadata frame and there is no previous P-frame.
                self.update_current_metadata(frame)

    def Work(self, p_frame, delimiter_frame):
        if "SCAN_HealpixNSide" not in p_frame:
            raise RuntimeError("SCAN_HealpixNSide not in frame")
        if "SCAN_HealpixPixel" not in p_frame:
            raise RuntimeError("SCAN_HealpixPixel not in frame")
        if "SCAN_PositionVariationIndex" not in p_frame:
            raise RuntimeError("SCAN_PositionVariationIndex not in frame")

        evname = p_frame["SCAN_EventName"].value
        nside  = p_frame["SCAN_HealpixNSide"].value
        pixel  = p_frame["SCAN_HealpixPixel"].value
        index = (evname,nside,pixel)
        posVarIndex = p_frame["SCAN_PositionVariationIndex"].value

        if index not in self.pixelNumToFramesMap:
            self.pixelNumToFramesMap[index] = [None]*self.NPosVar
            
        if self.pixelNumToFramesMap[index][posVarIndex] is None:
            self.cache_size += 1
                
        p_frame_copy = copy.copy(p_frame)
        del p_frame
        
        delimiter_frame_copy = copy.copy(delimiter_frame)
        del delimiter_frame
        
        p_frame_copy.purge()
        delimiter_frame_copy.purge()
        
        self.pixelNumToFramesMap[index][posVarIndex] = (p_frame_copy, delimiter_frame_copy, copy.copy(self.current_metadata))

        frames_list = self.pixelNumToFramesMap[index]

        numPixelsArrived = sum(1 for entry in frames_list if (entry is not None))

        if numPixelsArrived == self.NPosVar:
            # print("all scans arrived for pixel", index)
            bestItemIndex = None
            bestFrameLLH = None
            for i, item in enumerate(frames_list):
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
            for i, item in enumerate(frames_list):
                if i == bestItemIndex:
                    for mf in frames_list[i][2]:
                        self.PushFrame(mf[1])
                    self.PushFrame(frames_list[i][0])
                self.PushFrame(frames_list[i][1])

            # now remove the entry from the map (and de-allocate our local reference, too)
            del frames_list
            del self.pixelNumToFramesMap[index]
            
            self.cache_size -= self.NPosVar

    def Finish(self):
        if len(self.pixelNumToFramesMap) == 0:
            return

        print("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
        print(self.pixelNumToFramesMap)
        print("**** WARN ****  --  END")


def collect_pixels(broker, auth_token, topic_in, topic_base_out):
    # connect to pulsar
    client_service = PulsarClientService(
        BrokerURL=broker,
        AuthToken=auth_token,
    )

    receiver_service = ReceiverService(
        client_service=client_service,
        topic=topic_in,
        subscription_name='skymap-collector-sub',
        force_single_consumer=True,
    )

    ########## the tray
    tray = I3Tray()

    tray.Add(ReceivePFrameWithMetadata, "ReceivePFrameWithMetadata",
        ReceiverService=receiver_service,
        )

    def show_progress(frame):
        show_progress.pbar.set_postfix_str("Memory usage is {:.1f}MiB".format(memory_usage_psutil()), refresh=False)
        show_progress.pbar.update(1)
    show_progress.pbar = tqdm.tqdm(total=float("inf"), miniters=None, mininterval=1)
    tray.Add(show_progress, "show_progress")

    tray.Add(FindBestRecoResultForPixel, "FindBestRecoResultForPixel")
    
    #### Note: for memory optimization purposes, there are only empty metadata frames here. 
    #### So it is probably not a good idea to add any non queuing-related modules after
    #### "FindBestRecoResultForPixel".
    
    tray.Add(SendPFrameWithMetadata, "SendPFrameWithMetadata",
        ClientService=client_service,
        Topic=lambda frame: topic_base_out+frame["SCAN_EventName"].value, # send to the (dynamic) topic specified in the frame
        MetadataTopicBase=None, # no specific metadata topic, will be dynamic according to incoming frame tags - do NOT change this as we mess with the metadata frames
        ProducerName=None, # each worker is on its own, there are no specific producer names (otherwise deduplication would mess things up)
        )
    
    tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
        ReceiverService=receiver_service
        )

    tray.Execute()
    del tray
    
    del receiver_service
    del client_service
