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
from pulsar_icetray import SendPFrameWithMetadata

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
        print("Going to submit {} pixels".format(len(self.pixels_to_push)))

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
            self.CreatePFrame(nside=self.nside, pixel=next_pixel)
        else:
            # we are done.
            self.RequestSuspension()

    def CreatePFrame(self, nside, pixel):
        dec, ra = healpy.pix2ang(nside, pixel)
        dec = dec - numpy.pi/2.
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


def send_scan(frame_packet, broker, topic, metadata_topic, nside=1):
    tray = I3Tray()
    
    # create P frames for a GCDQp packet
    tray.AddModule(SendPixelsToScan, "SendPixelsToScan",
        FramePacket=frame_packet,
        NSide=nside,
        InputTimeName="HESE_VHESelfVetoVertexTime",
        InputPosName="HESE_VHESelfVetoVertexPos",
        OutputParticleName="MillipedeSeedParticle",
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
        pulsesName="SplitUncleanedInIcePulsesLatePulseCleaned")

    # now send all P-frames as pulsar messages
    tray.Add(SendPFrameWithMetadata, "SendPFrameWithMetadata",
        BrokerURL=broker,
        Topic=topic,
        MetadataTopic=metadata_topic,
        ProducerName="skymap_to_scan_producer-1",

        SubscriptionName="skymap-worker-sub",
        )
    
    tray.Execute()
    del tray
