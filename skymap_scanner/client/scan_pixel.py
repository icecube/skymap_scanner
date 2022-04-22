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
from ..mq_tools.pulsar_icetray import (
    AcknowledgeReceivedPFrame,
    PulsarClientService,
    ReceivePFrameWithMetadata,
    ReceiverService,
    SendPFrameWithMetadata,
)


def scan_pixel_distributed(
    broker,  # for pulsar
    auth_token,  # for pulsar
    topic_to_clients,  # for pulsar
    topic_from_clients,  # for pulsar
    all_partitions,  # for pulsar
    ExcludedDOMs,
    pulsesName,
    base_GCD_paths,
    base_GCD_filename,
):
    """Actually do the scan."""

    # pulsesName = "{5}"
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

    # ExcludedDOMs = {4}

    # find an available GCD base path
    stagers = dataio.get_stagers()
    # base_GCD_paths = {6}
    # base_GCD_filename = "{7}"

    # try to load the base file from the various possible input directories
    GCD_diff_base_handle = None
    if base_GCD_filename is not None and base_GCD_filename != "None":
        for GCD_base_dir in base_GCD_paths:
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
    client_service = PulsarClientService(
        BrokerURL=broker,
        AuthToken=auth_token,
    )

    receiver_service = ReceiverService(
        client_service=client_service,
        topic=topic_to_clients,
        subscription_name="skymap-worker-sub",
        subscribe_to_single_random_partition=not all_partitions # if the input is a partitioned topic, subscribe to only *one* partition
    )

    if all_partitions:
        receiving_from_partition = None
        receiving_from_partition_index = None
        print("This worker is receiving from all partitions")
    else:
        receiving_from_partition = receiver_service.chosen_partition()
        receiving_from_partition_index = receiver_service.chosen_partition_index()
        print("This worker is receiving from partition number {} [\"{}\"]".format(receiving_from_partition_index, receiving_from_partition))

    ########## the tray
    tray = I3Tray()
    # tray.context["I3FileStager"] = stagers

    tray.Add(ReceivePFrameWithMetadata, "ReceivePFrameWithMetadata",
        ReceiverService=receiver_service,
        MaxCacheEntriesPerFrameStop=100, # cache more (so we do not have to re-connect in case we are collecting many different events)
        )

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
    tray.Add(SendPFrameWithMetadata, "SendPFrameWithMetadata",
        ClientService=client_service,
        Topic=topic_from_clients,
        MetadataTopicBase=None, # no specific metadata topic, will be dynamic according to incoming frame tags
        ProducerName=None, # each worker is on its own, there are no specific producer names (otherwise deduplication would mess things up)
        PartitionKey=lambda frame: frame["SCAN_EventName"].value + '_' + str(frame["SCAN_HealpixNSide"].value) + '_' + str(frame["SCAN_HealpixPixel"].value),
        SendToSinglePartitionIndex=receiving_from_partition_index # send to a specific partition only (the same index we are receiving from)
        # IMPORTANT: this assumes the input and the output topic have the same number of partitions!
        )

    tray.Add(AcknowledgeReceivedPFrame, "AcknowledgeReceivedPFrame",
        ReceiverService=receiver_service
        )

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
    parser.add_option("--connect-worker-to-all-partitions", action="store_true",
        dest="CONNECT_WORKER_TO_ALL_PARTITIONS", help="In normal operation the worker will choose a random input partition and only receive from it (and only send to the matching output partition). If you set this, it will read from all partitions. Bad for performance, but should be used if you only have very few workers.")

    # get parsed args
    (options,args) = parser.parse_args()

    pulsesName = 'SplitUncleanedInIcePulsesLatePulseCleaned'
    ExcludedDOMs = [
        'CalibrationErrata',
        'BadDomsList',
        'DeepCoreDOMs',
        'SaturatedDOMs',
        'BrightDOMs',
        pulsesName+'TimeWindows',
    ]

    scan_pixel_distributed(
        broker=options.BROKER,
        auth_token=options.AUTH_TOKEN,
        topic_to_clients=options.TOPIC_TO_CLIENTS,
        topic_from_clients=options.TOPIC_FROM_CLIENTS,
        all_partitions=options.CONNECT_WORKER_TO_ALL_PARTITIONS,
        ExcludedDOMs=ExcludedDOMs,
        pulsesName=pulsesName,
        base_GCD_paths=config.GCD_base_dirs,
        base_GCD_filename='TEST_GCD_FILENAME',  # TODO
    )


if __name__ == "__main__":
    main()
