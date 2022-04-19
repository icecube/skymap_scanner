"""The Worker service.

Based on python/perform_scan.py
"""


# fmt: off
# mypy: ignore-errors
# pylint: skip-file

import datetime
import os
import platform

from I3Tray import I3Tray, I3Units
from icecube import dataio, distribute, icetray, photonics_service


def makeSurePulsesExist(frame, pulsesName):
    """TODO - add this to pre-data processing"""
    if pulsesName not in frame:
        raise RuntimeError("{0} not in frame".format(pulsesName))
    if pulsesName+"TimeWindows" not in frame:
        raise RuntimeError("{0} not in frame".format(pulsesName+"TimeWindows"))
    if pulsesName+"TimeRange" not in frame:
        raise RuntimeError("{0} not in frame".format(pulsesName+"TimeRange"))


def scan_pixel_distributed(
    host,
    port,
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
    c = distribute.I3DistributeClient(
        WorkerScriptHash=distribute.sha1_of_main_script(),      # this is to ensure only the correct script is sending replies to the server
        ServerURL=f"tcp://{host}:{port}",
        DoNotPreRequestWork=True, # only request work once the current item has been returned
        )

    ########## the tray
    tray = I3Tray()
    # tray.context["I3FileStager"] = stagers

    tray.Add("I3DistributeSource", Client=c)

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

    tray.Add("I3DistributeSink", Client=c)

    tray.AddModule('TrashCan', 'thecan')

    tray.Execute()
    tray.Finish()
    del tray


# fmt: on
def main(port, pulsesName, config, base_GCD_filename):
    """Start up Worker service."""
    ExcludedDOMs = [
        "CalibrationErrata",
        "BadDomsList",
        "DeepCoreDOMs",
        "SaturatedDOMs",
        "BrightDOMs",
        "SplitUncleanedInIcePulsesLatePulseCleanedTimeWindows",
    ]

    scan_pixel_distributed(
        platform.node(),
        port,
        ExcludedDOMs,
        pulsesName,
        config.GCD_base_dirs,
        base_GCD_filename,
    )


if __name__ == "__main__":
    DEFAULT_PORT = 5555
    DEFAULT_EXCLUDEDDOMS = []
    DEFAULT_NUMCLIENTS = 10
    DEFAULT_PULSESNAME = "SplitUncleanedInIcePulsesLatePulseCleaned"
    DEFAULT_BASE_GCD_PATHS = [os.path.join(os.environ["I3_DATA"], "GCD")]
    DEFAULT_BASE_GCD_FILENAME = "GeoCalibDetectorStatus_2015.57161_V0.i3.gz"
    DEFAULT_REMOTESUBMITPREFIX = ""
    main()
