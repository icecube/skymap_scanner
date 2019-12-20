from __future__ import print_function
from __future__ import absolute_import

import os
import platform
import datetime
import re

import config

from I3Tray import *
from icecube import icetray, dataio, dataclasses, recclasses, simclasses
from icecube import photonics_service, gulliver, gulliver_modules, millipede

from icecube import frame_object_diff
from icecube.frame_object_diff.segments import uncompress

from pulsar_icetray import ReceivePFrameWithMetadata, AcknowledgeReceivedPFrame, ReceiverService, SendPFrameWithMetadata

def scan_pixel(broker, topic_in, topic_out,
    pulsesName="SplitUncleanedInIcePulsesLatePulseCleaned"):

    ########## load data

    # At HESE energies, deposited light is dominated by the stochastic losses
    # (muon part emits so little light in comparison)
    # This is why we can use ems_mie instead of InfBareMu_mie even for tracks
    base = os.path.expandvars('$I3_DATA/photon-tables/splines/ems_mie_z20_a10.%s.fits')
    cascade_service = photonics_service.I3PhotoSplineService(base % "abs", base % "prob", 0)

    basemu = os.path.expandvars('$I3_DATA/photon-tables/splines/InfBareMu_mie_%s_z20a10_V2.fits')
    # muon_service = photonics_service.I3PhotoSplineService(basemu % "abs", basemu% "prob", 0)
    muon_service = None

    SPEScale = 0.99

    receiver_service = ReceiverService(
        broker_url=broker,
        topic=topic_in,
        subscription_name="skymap-worker-sub",
    )

    ########## the tray
    tray = I3Tray()

    tray.Add(ReceivePFrameWithMetadata, "ReceivePFrameWithMetadata",
        ReceiverService=receiver_service
        )

    ########## perform the fit

    def notifyStart(frame):
        print("got data - uncompressing GCD", datetime.datetime.now())
    tray.AddModule(notifyStart, "notifyStart")

    tray.Add(uncompress, "GCD_patch",
         keep_compressed=False,
         base_path=config.base_GCD_path)

    def notifyExclusions(frame):
        print("determining DOM exclusions for this event", datetime.datetime.now())
    tray.AddModule(notifyExclusions, "notifyExclusions")
    
    ExcludedDOMs = \
    tray.AddSegment(millipede.HighEnergyExclusions, 'millipede_DOM_exclusions',
        Pulses = pulsesName,
        ExcludeDeepCore='DeepCoreDOMs',
        ExcludeSaturatedDOMs='SaturatedDOMs',
        ExcludeBrightDOMs='BrightDOMs',
        BadDomsList='BadDomsList',
        CalibrationErrata='CalibrationErrata',
        SaturationWindows='SaturationWindows'
        )
    
    # I like having frame objects in there even if they are empty for some frames
    def createEmptyDOMLists(frame, ListNames=[]):
        for name in ListNames:
            if name in frame: continue
            frame[name] = dataclasses.I3VectorOMKey()
    tray.AddModule(createEmptyDOMLists, 'createEmptyDOMLists',
        ListNames = ["BrightDOMs"],
        Streams=[icetray.I3Frame.Physics])
    
    # add the late pulse exclusion windows
    ExcludedDOMs = ExcludedDOMs + [pulsesName+'LatePulseCleanedTimeWindows']
    
    def notify0(frame):
        print("starting a new fit!", datetime.datetime.now())
    tray.AddModule(notify0, "notify0")
    
    tray.AddService('MillipedeLikelihoodFactory', 'millipedellh',
        MuonPhotonicsService=muon_service,
        CascadePhotonicsService=cascade_service,
        ShowerRegularization=0,
        PhotonsPerBin=15,
        DOMEfficiency=SPEScale,
        ExcludedDOMs=ExcludedDOMs,
        PartialExclusion=True,
        ReadoutWindow=pulsesName+'TimeRange',
        Pulses=pulsesName,
        BinSigma=3)
    
    tray.AddService('I3GSLRandomServiceFactory','I3RandomService')
    tray.AddService('I3GSLSimplexFactory', 'simplex',
        MaxIterations=20000)
    
    tray.AddService('MuMillipedeParametrizationFactory', 'coarseSteps',
        MuonSpacing=0.*I3Units.m,
        ShowerSpacing=5.*I3Units.m,
        StepX = 10.*I3Units.m,
        StepY = 10.*I3Units.m,
        StepZ = 10.*I3Units.m,
        StepT = 0.,
        StepZenith = 0.,
        StepAzimuth = 0.,
        )
    tray.AddService('I3BasicSeedServiceFactory', 'vetoseed',
        FirstGuesses=['MillipedeSeedParticle'],
        TimeShiftType='TNone',
        PositionShiftType='None')

    tray.AddModule('I3SimpleFitter', 'MillipedeStarting1stPass',
        OutputName='MillipedeStarting1stPass',
        SeedService='vetoseed',
        Parametrization='coarseSteps',
        LogLikelihood='millipedellh',
        Minimizer='simplex')
    
    
    def notify1(frame):
        print("1st pass done!", datetime.datetime.now())
        print("MillipedeStarting1stPass", frame["MillipedeStarting1stPass"])
    tray.AddModule(notify1, "notify1")
    
    tray.AddService('MuMillipedeParametrizationFactory', 'fineSteps',
        MuonSpacing=0.*I3Units.m,
        ShowerSpacing=2.5*I3Units.m,
    
        StepX = 2.*I3Units.m,
        StepY = 2.*I3Units.m,
        StepZ = 2.*I3Units.m,
        StepT = 5.*I3Units.ns, # now, also fit for time
        StepZenith = 0.,
        StepAzimuth = 0.,
        )
    tray.AddService('I3BasicSeedServiceFactory', 'firstFitSeed',
        FirstGuess='MillipedeStarting1stPass',
        TimeShiftType='TNone',
        PositionShiftType='None')
    tray.AddModule('I3SimpleFitter', 'MillipedeStarting2ndPass',
        OutputName='MillipedeStarting2ndPass',
        SeedService='firstFitSeed',
        Parametrization='fineSteps',
        LogLikelihood='millipedellh',
        Minimizer='simplex')
    
    
    def notify2(frame):
        print("2nd pass done!", datetime.datetime.now())
        print("MillipedeStarting2ndPass", frame["MillipedeStarting2ndPass"])
    tray.AddModule(notify2, "notify2")
    
    # now send the topic!
    tray.Add(SendPFrameWithMetadata, "SendPFrameWithMetadata",
        BrokerURL=broker,
        # # A dynamic topic. Topic name is a function converting the input topic name to an
        # # output name.
        # Topic=lambda x: re.sub(r'^{}'.format(topic_in), topic_out, x),
        
        Topic=topic_out,
        MetadataTopic=None, # no specific metadata topic, will be dynamic according to incoming frame tags
        # ProducerName="skymap_scan_to_collector_producer-1",
        
        ReceiverForceSingleConsumer=True,
        SubscriptionName="skymap-collector-sub",
        )
    
    tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
        ReceiverService=receiver_service
        )

    tray.Execute()
    del tray
    
    del receiver_service
