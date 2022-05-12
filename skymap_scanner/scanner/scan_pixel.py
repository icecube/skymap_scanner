"""Scan a single pixel.

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
import datetime
import logging
import os
import pickle
from typing import Any, List, Tuple

import coloredlogs  # type: ignore[import]
from I3Tray import I3Tray, I3Units  # type: ignore[import]
from icecube import millipede  # type: ignore[import]  # noqa: F401
from icecube import dataio, icetray, photonics_service

from .. import config

LOGGER = logging.getLogger("skymap-scanner-client-scanner")


class InjectFrames(icetray.I3Module):  # type: ignore[misc]
    """Push Pixel PFrame into tray along with GCDQp frames."""

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        self.AddParameter("Pixel", "Pixel PFrame", None)
        self.AddParameter("GCDQpFrames", "GCDQp packet (list of frames)", [])

    def Configure(self) -> None:
        self.pixel = self.GetParameter("Pixel")
        if not self.pixel:
            raise RuntimeError("self.pixel is not set")

        self.gcdqp_frames = self.GetParameter("GCDQpFrames")
        if not self.gcdqp_frames:
            raise RuntimeError("self.gcdqp_frames is empty")

    def Process(self) -> None:
        """Push the given frames."""
        if self.PopFrame():
            raise RuntimeError("InjectFrames needs to be used as a driving module")

        for frame in self.gcdqp_frames:
            self.PushFrame(frame)
        self.PushFrame(self.pixel)


def get_GCD_diff_base_handle(base_GCD_filename_url: str) -> str:
    # find an available GCD base path
    stagers = dataio.get_stagers()

    # try to load the base file from the various possible input directories
    GCD_diff_base_handle = None
    if base_GCD_filename_url not in [None, 'None']:
        for GCD_base_dir in config.GCD_base_dirs:
            try:
                read_url = os.path.join(GCD_base_dir, base_GCD_filename_url)
                LOGGER.debug("reading baseline GCD from {0}".format( read_url ))
                GCD_diff_base_handle = stagers.GetReadablePath( read_url )
                if not os.path.isfile( str(GCD_diff_base_handle) ):
                    raise RuntimeError("file does not exist (or is not a file)")
            except:
                LOGGER.debug(" -> failed")
                GCD_diff_base_handle=None
            if GCD_diff_base_handle is not None:
                LOGGER.debug(" -> success")
                break

        if GCD_diff_base_handle is None:
            raise RuntimeError("Could not read the input GCD file '{0}' from any pre-configured location".format(base_GCD_filename_url))

    return GCD_diff_base_handle


def read_in_file(in_file: str) -> Tuple[icetray.I3Frame, List[icetray.I3Frame], str]:
    """Get event info and pixel from reading the in-file."""
    with open(in_file, "rb") as f:
        payload = pickle.load(f)

    pframe = payload['Pixel_PFrame']
    gcdqp_frames = payload['GCDQp_Frames']
    base_GCD_filename_url = payload['base_GCD_filename_url']

    return pframe, gcdqp_frames, get_GCD_diff_base_handle(base_GCD_filename_url)


def scan_pixel(
    pframe: icetray.I3Frame,
    gcdqp_frames: List[icetray.I3Frame],
    GCD_diff_base_handle: str,
    out_file: str,
) -> str:
    """Actually do the scan."""
    LOGGER.info(
        f"Scanning pixel {str(pframe)=}, {str(gcdqp_frames)=}, {str(GCD_diff_base_handle)=}"
    )

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

    # basemu = os.path.expandvars('$I3_DATA/photon-tables/splines/InfBareMu_mie_%s_z20a10_V2.fits')
    # muon_service = photonics_service.I3PhotoSplineService(basemu % "abs", basemu% "prob", 0)
    muon_service = None

    # iceModelBaseNames = {"SpiceMie": "ems_mie_z20_a10", "Spice1": "ems_spice1_z20_a10"}
    # iceModelBaseName = iceModelBaseNames["SpiceMie"]

    SPEScale = 0.99

    tray = I3Tray()

    # Inject the frames
    tray.AddModule(
        InjectFrames,
        "InjectFrames",
        Pixel=pframe,
        GCDQpFrames=gcdqp_frames,
    )

    def makeSurePulsesExist(frame_stream) -> None:
        print(f"{type(frame_stream)=}")
        pulsesName = "SplitUncleanedInIcePulsesLatePulseCleaned"
        if pulsesName not in frame_stream:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName+"TimeWindows" not in frame_stream:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeWindows"))
        if pulsesName+"TimeRange" not in frame_stream:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeRange"))

    tray.AddModule(makeSurePulsesExist, "makeSurePulsesExist")

    ########## perform the fit

    def notifyStart(frame):
        LOGGER.debug("got data - uncompressing GCD", datetime.datetime.now())
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
        LOGGER.debug("starting a new fit!", datetime.datetime.now())
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
        LOGGER.debug("1st pass done!", datetime.datetime.now())
        LOGGER.debug("MillipedeStarting1stPass", frame["MillipedeStarting1stPass"])
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
        LOGGER.debug("2nd pass done!", datetime.datetime.now())
        LOGGER.debug("MillipedeStarting2ndPass", frame["MillipedeStarting2ndPass"])
    tray.AddModule(notify2, "notify2")

    # Write scan out
    def write_scan(frame: icetray.I3Frame) -> None:
        if frame.Stop != icetray.I3Frame.Physics:
            return
        if os.path.exists(out_file):  # will guarantee only one PFrame is written
            raise FileExistsError(out_file)
        with open(out_file, 'wb') as f:
            LOGGER.info(f"Pickle-dumping scan ({frame=}) to {out_file}.")
            pickle.dump(frame, f)
    tray.AddModule(write_scan, "write_scan")

    tray.AddModule('TrashCan', 'thecan')

    LOGGER.info("Staring IceTray...")
    tray.Execute()
    tray.Finish()
    del tray
    LOGGER.info("Done with IceTray.")

    if not os.path.exists(out_file):
        raise FileNotFoundError(f"Out file was not written: {out_file}")

    return out_file


# fmt: on
def main() -> None:
    """Scan a single pixel."""
    parser = argparse.ArgumentParser(
        description=(
            "Perform millipede reconstruction scans on a pixel "
            "by reading `--in-file FILE` and writing result to "
            "`--out-file FILE`."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--in-file",
        required=True,
        help="a file containing the pixel to scan",
    )
    parser.add_argument(
        "--out-file",
        required=True,
        help="a file to write the reco scan to",
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
        LOGGER.warning(f"{arg}: {val}")

    pframe, gcdqp_frames, GCD_diff_base_handle = read_in_file(args.in_file)

    scan_pixel(pframe, gcdqp_frames, GCD_diff_base_handle, args.out_file)
    LOGGER.info("Done scanning pixel.")


if __name__ == "__main__":
    main()
