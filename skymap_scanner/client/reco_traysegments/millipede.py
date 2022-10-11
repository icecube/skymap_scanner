"""IceTray segment for a millipede reco."""

# fmt: off
# pylint: skip-file

import datetime

from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    dataclasses,
    dataio,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    millipede,
    photonics_service,
    recclasses,
    simclasses,
)

from ... import config as cfg


@icetray.traysegment
def millipede_traysegment(tray, name, muon_service, cascade_service, ExcludedDOMs, pulsesName, logger):
    """Perform Millipede reco."""

    def notify0(frame):
        logger.debug(f"starting a new fit ({name})! {datetime.datetime.now()}")

    tray.AddModule(notify0, "notify0")

    tray.AddService('MillipedeLikelihoodFactory', 'millipedellh',
        MuonPhotonicsService=muon_service,
        CascadePhotonicsService=cascade_service,
        ShowerRegularization=0,
        PhotonsPerBin=15,
        # DOMEfficiency=SPEScale, # moved to cascade_service.SetEfficiencies(SPEScale)
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
        FirstGuesses=[cfg.OUTPUT_PARTICLE_NAME],
        TimeShiftType='TNone',
        PositionShiftType='None')

    tray.AddModule('I3SimpleFitter', 'MillipedeStarting1stPass',
        OutputName='MillipedeStarting1stPass',
        SeedService='vetoseed',
        Parametrization='coarseSteps',
        LogLikelihood='millipedellh',
        Minimizer='simplex')

    def notify1(frame):
        logger.debug(f"1st pass done! {datetime.datetime.now()}")
        logger.debug(f"MillipedeStarting1stPass: {frame['MillipedeStarting1stPass']}")

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
        logger.debug(f"2nd pass done! {datetime.datetime.now()}")
        logger.debug(f"MillipedeStarting2ndPass: {frame['MillipedeStarting2ndPass']}")

    tray.AddModule(notify2, "notify2")
