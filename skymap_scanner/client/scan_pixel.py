"""The Client service.

Based on:
    python/perform_scan.py
        - only 8 lines starting with `tray.AddSegment(, "scan_pixel_distributed",`
    python/traysegments/scan_pixel_distributed.py
        - a lot of similar code
    cloud_tools/scan_pixel.py
        - Pulsar logic
"""

# fmt: off
# mypy: ignore-errors
# pylint: skip-file

import datetime
import os
from optparse import OptionParser

from I3Tray import I3Tray, I3Units
from icecube import dataio, icetray, photonics_service

from .. import config


def scan_pixel_distributed(
    broker,  # for pulsar
    auth_token,  # for pulsar
    topic_to_clients,  # for pulsar
    topic_from_clients,  # for pulsar
    ExcludedDOMs,
    pulsesName,
):
    """Actually do the scan."""

    ########## load data
    # At HESE energies, deposited light is dominated by the stochastic losses
    # (muon part emits so little light in comparison)
    # This is why we can use ems_mie instead of InfBareMu_mie even for tracks
    base = os.path.expandvars('$I3_DATA/photon-tables/splines/ems_mie_z20_a10.%s.fits')
    cascade_service = photonics_service.I3PhotoSplineService(base % "abs", base % "prob", 0)

    basemu = os.path.expandvars('$I3_DATA/photon-tables/splines/InfBareMu_mie_%s_z20a10_V2.fits')
    # muon_service = photonics_service.I3PhotoSplineService(basemu % "abs", basemu% "prob", 0)
    muon_service = None

    iceModelBaseNames = {{"SpiceMie": "ems_mie_z20_a10", "Spice1": "ems_spice1_z20_a10"}}
    iceModelBaseName = iceModelBaseNames["SpiceMie"]

    SPEScale = 0.99

    # TODO - MQClient: receive needed state_dict info: GCDQp Frames & base_GCD_filename
    # TODO - -> payload={'event_id':id, 'gcd_data':{'GCDQp_Frames':[...], 'base_GCD_filename_url':base_GCD_filename}}
    # TODO - -> cache

    # find an available GCD base path
    stagers = dataio.get_stagers()

    # try to load the base file from the various possible input directories
    GCD_diff_base_handle = None
    if base_GCD_filename is not None and base_GCD_filename != "None":
        for GCD_base_dir in config.GCD_base_dirs:
            try:
                read_url = os.path.join(GCD_base_dir, base_GCD_filename)
                print("reading baseline GCD from {0}".format( read_url ))
                GCD_diff_base_handle = stagers.GetReadablePath( read_url )
                if not os.path.isfile( str(GCD_diff_base_handle) ):
                    raise RuntimeError("file does not exist (or is not a file)")
            except:
                print(" -> failed")
                GCD_diff_base_handle=None
            if GCD_diff_base_handle is not None:
                print(" -> success")
                break

        if GCD_diff_base_handle is None:
            raise RuntimeError("Could not read the input GCD file '{0}' from any pre-configured location".format(base_GCD_filename))

    # connect to a server
    # connect to pulsar
    # client_service = PulsarClientService(
    #     BrokerURL=broker,
    #     AuthToken=auth_token,
    # )

    # receiver_service = ReceiverService(
    #     client_service=client_service,
    #     topic=topic_to_clients,
    #     subscription_name="skymap-worker-sub",
    # )

    ########## the tray
    tray = I3Tray()
    # tray.context["I3FileStager"] = stagers

    # tray.Add(ReceivePFrame, "ReceivePFrame",
    #     ReceiverService=receiver_service,
    #     MaxCacheEntriesPerFrameStop=100, # cache more (so we do not have to re-connect in case we are collecting many different events)
    #     )

    # TODO - MQClient: receive each msg: payload={'frame':frame}
    # TODO - -> push gcd frames from cache (above)
    # TODO - -> push frame

    ########## perform the fit

    def notifyStart(frame):
        print("got data - uncompressing GCD", datetime.datetime.now())
    tray.AddModule(notifyStart, "notifyStart")

    @icetray.traysegment
    def UncompressGCD(tray,name, base_GCD_path, base_GCD_filename):
        from icecube.frame_object_diff.segments import uncompress

        tray.Add(uncompress, name+"_GCD_patch",
                 keep_compressed=False,
                 base_path=base_GCD_path,
                 base_filename=base_GCD_filename)

    if GCD_diff_base_handle is not None:
        tray.Add(UncompressGCD, "GCD_uncompress",
                 base_GCD_path="",
                 base_GCD_filename=str(GCD_diff_base_handle))

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
    # tray.Add(SendPFrame, "SendPFrame",
    #     ClientService=client_service,
    #     Topic=topic_from_clients,
    #     ProducerName=None, # each worker is on its own, there are no specific producer names (otherwise deduplication would mess things up)
    #     )

    # tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
    #     ReceiverService=receiver_service
    #     )

    # TODO - MQClient: send frame
    # TODO - MQClient: ack? or do we ack up top then there's server-side logic that detects dropped clients?

    tray.AddModule('TrashCan', 'thecan')

    tray.Execute()
    tray.Finish()
    del tray

    del receiver_service
    del client_service


def main():
    """Start up Client service."""

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
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

    scan_pixel_distributed(
        broker=options.BROKER,
        auth_token=options.AUTH_TOKEN,
        topic_to_clients=options.TOPIC_TO_CLIENTS,
        topic_from_clients=options.TOPIC_FROM_CLIENTS,
    )


if __name__ == "__main__":
    main()
