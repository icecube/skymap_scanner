from __future__ import print_function
from __future__ import absolute_import

import numpy
import healpy
import os
import random

import tqdm
import time

from icecube import icetray, dataclasses
from icecube import gulliver, millipede
from icecube import astro
from icecube import VHESelfVeto
from icecube import frame_object_diff
from icecube.frame_object_diff.segments import uncompress
from I3Tray import *

import config

from utils import get_event_mjd, create_pixel_list
from pulsar_icetray import PulsarClientService, SendPFrameWithMetadata

class SendPixelsToScan(icetray.I3Module):
    def __init__(self, ctx):
        super(SendPixelsToScan, self).__init__(ctx)
        self.AddParameter("FramePacket", "The GCDQp frame packet to send", None)
        
        self.AddParameter("NSide", "The healpix resolution in terms of \"nside\".", 8)

        self.AddParameter("AreaCenterNSide", "The healpix nside of the center pixel defined in \"AreaCenterPixel\".", None)
        self.AddParameter("AreaCenterPixel", "The healpix pixel number where the area to be scanned is centered.", None)
        self.AddParameter("AreaNumPixels",   "The number of pixels in the area to be scanned (this is in terms of \"NSide\").", None)

        self.AddParameter("InputTimeName", "Name of an I3Double to use as the vertex time for the coarsest scan", "HESE_VHESelfVetoVertexTime")
        self.AddParameter("InputPosName", "Name of an I3Position to use as the vertex position for the coarsest scan", "HESE_VHESelfVetoVertexPos")
        self.AddParameter("OutputParticleName", "Name of the output I3Particle", "MillipedeSeedParticle")
        self.AddParameter("InjectEventName", "Event name in each P-frame - for later sorting", None)
        self.AddParameter("PosVariations", "An array of positional offsets to use for each pixel", [dataclasses.I3Position(0.,0.,0.)])
        self.AddOutBox("OutBox")

    def Configure(self):
        self.GCDQpFrames = self.GetParameter("FramePacket")
        self.nside = self.GetParameter("NSide")
        self.input_pos_name = self.GetParameter("InputPosName")
        self.input_time_name = self.GetParameter("InputTimeName")
        self.output_particle_name = self.GetParameter("OutputParticleName")
        self.inject_event_name = self.GetParameter("InjectEventName")
        self.posVariations = self.GetParameter("PosVariations")
        
        self.area_center_nside = self.GetParameter("AreaCenterNSide")
        self.area_center_pixel = self.GetParameter("AreaCenterPixel")
        self.area_num_pixels = self.GetParameter("AreaNumPixels")

        if (self.area_center_nside is not None or self.area_center_pixel is not None or self.area_num_pixels is not None) and \
           (self.area_center_nside is     None or self.area_center_pixel is     None or self.area_num_pixels is     None):
           raise RuntimeError("You have to either set none of the three options AreaCenterNSide,AreaCenterPixel,AreaNumPixels or all of them")

        p_frame = self.GCDQpFrames[-1]
        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.seed_position = p_frame[self.input_pos_name]
        self.seed_time = p_frame[self.input_time_name].value
        self.seed_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_mjd = get_event_mjd(self.GCDQpFrames)

        # self.pixels_to_push = range(healpy.nside2npix(self.nside))
        self.pixels_to_push = create_pixel_list(
            self.nside,
            area_center_nside=self.area_center_nside,
            area_center_pixel=self.area_center_pixel,
            area_num_pixels=self.area_num_pixels
            )
        
        print("Going to submit {} pixels".format(len(self.pixels_to_push)))
        
        self.pixel_index = 0
        
    def Process(self):
        # driving module - we will be called repeatedly by IceTray with no input frames
        if self.PopFrame():
            raise RuntimeError("SendPixelsToScan needs to be used as a driving module")

        # push GCDQp packet if not done so already
        if self.GCDQpFrames:
            for frame in self.GCDQpFrames:
                self.PushFrame(frame)
            self.GCDQpFrames = None
            print("Commencing full-sky scan...")
            return

        # submit one more pixel
        if len(self.pixels_to_push) > 0:
            # get the first item from the list and remove it from the list
            next_pixel = self.pixels_to_push.pop(0)
            
            # create and push a P-frame to be processed
            self.CreatePFrame(nside=self.nside, pixel=next_pixel, pixel_index=self.pixel_index)
            self.pixel_index+=1
        else:
            # we are done.
            self.RequestSuspension()

    def CreatePFrame(self, nside, pixel, pixel_index):
        dec, ra = healpy.pix2ang(nside, pixel)
        dec = dec - numpy.pi/2.
        zenith, azimuth = astro.equa_to_dir(ra, dec, self.event_mjd)
        zenith = float(zenith)
        azimuth = float(azimuth)
        direction = dataclasses.I3Direction(zenith,azimuth)

        position = self.seed_position
        time = self.seed_time
        energy = self.seed_energy

        for i in range(0,len(self.posVariations)):
            posVariation = self.posVariations[i]
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

            # an overall sequence index, 0-based, in case we need to re-start
            p_frame["SCAN_EventOverallIndex"] = icetray.I3Int( int(i) + pixel_index*len(self.posVariations))
            if self.inject_event_name is not None:
                p_frame["SCAN_EventName"] = dataclasses.I3String(self.inject_event_name)

            self.PushFrame(p_frame)


def send_scan(frame_packet, broker, auth_token, topic, metadata_topic_base, event_name, nside=1, area_center_nside=None, area_center_pixel=None, area_num_pixels=None):
    if (area_center_nside is not None or area_center_pixel is not None or area_num_pixels is not None) and \
       (area_center_nside is None or area_center_pixel is None or area_num_pixels is None):
       raise RuntimeError("You have to either set none of the three options area_center_nside,area_center_pixel,area_num_pixels or all of them")
    
    if area_center_nside is None:
        producer_name = "skymap_to_scan_producer-" + event_name + "-nside" + str(nside)
    else:
        producer_name = "skymap_to_scan_producer-" + event_name + "-nside" + str(nside) + "-Cn" + str(area_center_nside) + "-p" + str(area_center_pixel)
    
    print("producer_name is {}".format(producer_name))
    
    # set up the positional variations (we use 7)
    variationDistance = 20.*I3Units.m
    posVariations = [
        dataclasses.I3Position(0.,0.,0.),
        dataclasses.I3Position(-variationDistance,0.,0.),
        dataclasses.I3Position( variationDistance,0.,0.),
        dataclasses.I3Position(0.,-variationDistance,0.),
        dataclasses.I3Position(0., variationDistance,0.),
        dataclasses.I3Position(0.,0.,-variationDistance),
        dataclasses.I3Position(0.,0., variationDistance)
        ]

    if area_num_pixels is None:
        num_pix = healpy.nside2npix(nside)
    else:
        num_pix = area_num_pixels
    num_it = num_pix*len(posVariations)
    pbar = tqdm.tqdm(
        total=num_it,
        desc = event_name,
        ascii = " .oO0",
        leave = True
        )

    # connect to pulsar
    client_service = PulsarClientService(
        BrokerURL=broker,
        AuthToken=auth_token
    )

    tray = I3Tray()
    
    # create P frames for a GCDQp packet
    tray.AddModule(SendPixelsToScan, "SendPixelsToScan",
        FramePacket=frame_packet,
        NSide=nside,
        InputTimeName="HESE_VHESelfVetoVertexTime",
        InputPosName="HESE_VHESelfVetoVertexPos",
        OutputParticleName="MillipedeSeedParticle",
        InjectEventName=event_name,
        PosVariations=posVariations,
        AreaCenterNSide=area_center_nside,
        AreaCenterPixel=area_center_pixel,
        AreaNumPixels=area_num_pixels
    )

    # sanity check
    def makeSurePulsesExist(frame, pulsesName):
        if pulsesName not in frame:
            print(frame)
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName+"TimeWindows" not in frame:
            print(frame)
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeWindows"))
        if pulsesName+"TimeRange" not in frame:
            print(frame)
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeRange"))
    tray.AddModule(makeSurePulsesExist, "makeSurePulsesExist",
        pulsesName="SplitInIcePulsesLatePulseCleaned")

    # now send all P-frames as pulsar messages
    tray.Add(SendPFrameWithMetadata, "SendPFrameWithMetadata",
        ClientService=client_service,
        Topic=topic,
        MetadataTopicBase=metadata_topic_base,
        ProducerName=producer_name,
        I3IntForSequenceID="SCAN_EventOverallIndex",
        PartitionKey=lambda frame: frame["SCAN_EventName"].value + '_' + str(frame["SCAN_HealpixNSide"].value) + '_' + str(frame["SCAN_HealpixPixel"].value)
        )
    
    def update_pbar(frame):
        pbar.set_postfix(pixel="{}/{}".format(frame["SCAN_EventOverallIndex"].value/len(posVariations)+1, num_pix), refresh=False)
        pbar.update(1)
    tray.Add(update_pbar, "update_pbar")
    
    tray.Execute()
    del tray

    pbar.close()

    del client_service
