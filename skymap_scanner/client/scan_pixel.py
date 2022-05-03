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
# pylint: skip-file

import argparse
import asyncio
import datetime
import logging
import os
from typing import List, Tuple

import coloredlogs  # type: ignore[import]
import mqclient_pulsar as mq
from I3Tray import I3Tray, I3Units  # type: ignore[import]
from icecube import dataio, icetray, photonics_service  # type: ignore[import]

from .. import config


class MessagesToFrames(icetray.I3Module):
    """Consume message queue and push frames into tray along with GCDQp frames."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.AddParameter("MQClient", "MQClient client", None)
        self.AddParameter("GCDQpFrames", "MQClient client", [])

    def Configure(self):
        self.mqclient = self.GetParameter("MQClient")
        if not self.mqclient:
            raise RuntimeError("self.mqclient is not set")

        self.gcdqp_frames = self.GetParameter("GCDQpFrames")
        if not self.gcdqp_frames:
            raise RuntimeError("self.gcdqp_frames is empty")

    def Process(self):
        if self.PopFrame():
            raise RuntimeError("FrameArrayReader needs to be used as a driving module")

        # TODO - MQClient: receive each msg: payload={'frame':frame}
        for msg in [object()]*100:
            # Push GCD Frames
            # TODO - -> push gcd frames from cache (above)
            # Push Pixel
            frame = msg  # TODO
            self.PushFrame(frame)


class FramesToMessages(icetray.I3Module):
    """Grab each PFrame and send as a message to queue."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.AddParameter("MQClient", "MQClient client", None)

    def Configure(self):
        self.mqclient = self.GetParameter("MQClient")
        if not self.mqclient:
            raise RuntimeError("self.mqclient is not set")

    def Physics(self, frame):
        msg = frame  # TODO
        self.mqclient.send(msg)  # TODO
        self.PushFrame(frame)


def get_GCD_diff_base_handle(base_GCD_filename_url: str) -> str:
    # find an available GCD base path
    stagers = dataio.get_stagers()

    # try to load the base file from the various possible input directories
    GCD_diff_base_handle = None
    if base_GCD_filename_url not in [None, 'None']:
        for GCD_base_dir in config.GCD_base_dirs:
            try:
                read_url = os.path.join(GCD_base_dir, base_GCD_filename_url)
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
            raise RuntimeError("Could not read the input GCD file '{0}' from any pre-configured location".format(base_GCD_filename_url))

    return GCD_diff_base_handle


async def get_event_metadata(
    event_id_string: str,
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
) -> Tuple[str, List[icetray.I3Frame]]:
    """Send metadata for event to client(s): GCDQp Frames & base_GCD_filename."""
    queue = mq.Queue(
        address=broker, name=f"event-metadata-{event_id_string}", auth_token=auth_token
    )
    async with queue.open_sub_one() as msg:
        return (
            get_GCD_diff_base_handle(msg["base_GCD_filename_url"]),
            msg["GCDQp_Frames"],
        )

    raise RuntimeError("Metadata not received")


async def scan_pixel_distributed(
    event_id_string: str,
    broker: str,  # for pulsar
    auth_token: str,  # for pulsar
    topic_to_clients: str,  # for pulsar
    topic_from_clients: str,  # for pulsar
) -> None:
    """Actually do the scan."""
    GCD_diff_base_handle, gcdqp_frames = await get_event_metadata(
        event_id_string, broker, auth_token
    )

    # connect to queues
    from_server_queue = object()  # TODO
    to_server_queue = object()  # TODO

    pulsesName = 'SplitUncleanedInIcePulsesLatePulseCleaned'
    ExcludedDOMs = [
        'CalibrationErrata',
        'BadDomsList',
        'DeepCoreDOMs',
        'SaturatedDOMs',
        'BrightDOMs',
        pulsesName+'TimeWindows',
    ]

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

    tray = I3Tray()

    # Get Pixels/Frames/Messages
    tray.AddModule(
        MessagesToFrames,
        "MessagesToFrames",
        MQClient=from_server_queue,
        GCDQpFrames=gcdqp_frames,
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

    # Send Scans/Frames/Messages
    tray.AddModule(
        FramesToMessages,
        "FramestoMessages",
        MQClient=to_server_queue,
    )

    # TODO - MQClient: ack? or do we ack up top then there's server-side logic that detects dropped clients?

    tray.AddModule('TrashCan', 'thecan')

    tray.Execute()
    tray.Finish()
    del tray


# fmt: on
def main() -> None:
    """Start up Client service."""
    parser = argparse.ArgumentParser(
        description=(
            "Start up client daemon to perform millipede scans on pixels "
            "received from the server for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-e",
        "--event-id",
        required=True,
        help="The ID of the event to scan",
    )
    parser.add_argument(
        "-t",
        "--topics-root",
        default="persistent://icecube/skymap/",
        help="A root/prefix to base topic names for communicating to/from client(s)",
    )
    parser.add_argument(
        "-b",
        "--broker",
        default="pulsar://localhost:6650",
        help="The Pulsar broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
        help="The Pulsar authentication token to use",
    )
    parser.add_argument(
        "-l",
        "--log",
        default="INFO",
        help="the output logging level",
    )

    args = parser.parse_args()
    coloredlogs.install(level=args.log)
    for arg, val in vars(args).items():
        logging.warning(f"{arg}: {val}")

    asyncio.get_event_loop().run_until_complete(
        scan_pixel_distributed(
            event_id_string=args.event_id,
            broker=args.broker,
            auth_token=args.auth_token,
            topic_to_clients=os.path.join(args.topics_root, "to-client", args.event_id),
            topic_from_clients=os.path.join(
                args.topics_root, "from-client", args.event_id
            ),
        )
    )


if __name__ == "__main__":
    main()
