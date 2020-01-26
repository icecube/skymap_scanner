from __future__ import print_function
from __future__ import absolute_import

import os
import numpy
import tqdm

import config

from I3Tray import *
from icecube import icetray, dataio, dataclasses
from icecube import VHESelfVeto
from icecube.frame_object_diff.segments import uncompress

from pulsar_icetray import ReceivePFrameWithMetadata, AcknowledgeReceivedPFrame, PulsarClientService, ReceiverService, SendPFrameWithMetadata

class WaitForNumberOfPFrames(icetray.I3Module):
    def __init__(self, ctx):
        super(WaitForNumberOfPFrames, self).__init__(ctx)
        self.AddOutBox("OutBox")
        self.AddParameter("NPFrames", "Number of P-frames to collect before pushing all of them", 7)

    def Configure(self):
        self.NPFrames = self.GetParameter("NPFrames")

        self.pixelNumToFramesMap = {}
        self.last_p_frame = None
        self.seen_all_frames = False
        
        self.last_pixel_num_done = 0
        self.pbar = tqdm.tqdm(total=self.NPFrames)

    def report_progress(self):
        pixel_num_done = len(self.pixelNumToFramesMap)
        if pixel_num_done > self.last_pixel_num_done:
            increment = pixel_num_done-self.last_pixel_num_done
            self.last_pixel_num_done = pixel_num_done
            self.pbar.update(increment)

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
                    raise RuntimeError("already received all frames ({}). Received another one.".format(self.NPFrames))

                self.report_progress()
                
                # it's a physics frame. store it and return
                self.last_p_frame = frame
                return
            else:
                # it's some other frame and there is no previous P-frame.
                # Just push this one
                self.PushFrame(frame)
        

    def Work(self, p_frame, delimiter_frame):
        nside = p_frame["SCAN_HealpixNSide"].value
        pixel = p_frame["SCAN_HealpixPixel"].value
        index = (nside,pixel)

        if index in self.pixelNumToFramesMap:
            print("**** Pixel {} has already been seen. Ignoring this copy!".format(index))
            #self.PushFrame(p_frame) # p-frame -> do NOT push, eat this pixel
            self.PushFrame(delimiter_frame) # delimiter frame -> acknowledge this superfluous frame
            return

        self.pixelNumToFramesMap[index] = (p_frame, delimiter_frame)

        if len(self.pixelNumToFramesMap) >= self.NPFrames:
            print("All frames arrived, pushing all frames.")
            
            for key in sorted(self.pixelNumToFramesMap.keys()):
                self.PushFrame(self.pixelNumToFramesMap[key][0]) # p-frame
                self.PushFrame(self.pixelNumToFramesMap[key][1]) # delimiter frame
                del self.pixelNumToFramesMap[key]

            # allow no more P-frames from now on
            self.seen_all_frames = True
        
            self.RequestSuspension()
            

    def Finish(self):
        if len(self.pixelNumToFramesMap) == 0:
            return

        print("**** WARN ****  --  pixels left in cache, not all of the packets seem to be complete")
        print(self.pixelNumToFramesMap)
        print("**** WARN ****  --  END")
        
        self.pbar.close()



def save_pixels(broker, auth_token, topic_in, filename_out, expected_n_frames, delete_from_queue=True):
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
        NPFrames=expected_n_frames)

    tray.Add(uncompress, "GCD_uncompress",
             keep_compressed=False,
             base_path=config.base_GCD_path)
    
    tray.Add("I3Writer", "writer",
             Filename=filename_out,
             SkipKeys=['__msgid', '__msgtopic'],
             Streams=[
                   icetray.I3Frame.Geometry,
                   icetray.I3Frame.Calibration,
                   icetray.I3Frame.DetectorStatus,
                   icetray.I3Frame.DAQ,
                   icetray.I3Frame.Physics,
                   icetray.I3Frame.Stream('p')
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
