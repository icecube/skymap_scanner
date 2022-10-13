"""IceTray segment for a millipede reco."""

# fmt: off

import datetime
from typing import Tuple

import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    VHESelfVeto,
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
    lilliput,
)
from icecube.icetray import I3Frame

from .. import config as cfg
from ..utils.pixelreco import PixelReco
from . import RecoInterface


class Millipede(RecoInterface):
    """Reco logic for millipede."""

    @icetray.traysegment
    def traysegment(tray, name, muon_service, cascade_service, ExcludedDOMs, pulsesName, logger, seed=None):
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
            BinSigma=3,
            RelUncertainty=0.3)

        tray.AddService('I3GSLRandomServiceFactory','I3RandomService')

        tray.context['isimplex'] = lilliput.IMinuitMinimizer(
            MaxIterations=2000,
            Tolerance=0.1,
            Algorithm="SIMPLEX",
        )
        tray.context['imigrad'] = lilliput.IMinuitMinimizer(
            MaxIterations=1000,
            Tolerance=0.1,
            Algorithm="MIGRAD",
            WithGradients=True,
            FlatnessCheck=False,
            IgnoreEDM=True, # Don't report convergence failures
            CheckGradient=False, # Don't die on gradient errors
            MinuitStrategy=0, # Don't try to check local curvature
            )

        ## TODO: try this MIGRAD, which fails
        # tray.AddService("I3GulliverMinuit2Factory", 'migrad',
        #                 MaxIterations=1000,
        #                 Tolerance=0.1,
        #                 Algorithm="MIGRAD",
        #                 WithGradients=True,
        #                 FlatnessCheck=False,
        #                 IgnoreEDM=True, # Don't report convergence failures
        #                 CheckGradient=False, # Don't die on gradient errors
        #                 MinuitStrategy=0, # Don't try to check local curvature
        #                 )

        coars_steps = dict(StepX=10.*I3Units.m,
                           StepY=10.*I3Units.m,
                           StepZ=10.*I3Units.m,
                           StepZenith=0.,
                           StepAzimuth=0.,
                           StepT=25.*I3Units.ns,
                           ShowerSpacing=5.*I3Units.m,
                           MuonSpacing=0,
                           Boundary=700*I3Units.m)
        finer_steps = dict(StepX=2.*I3Units.m,
                           StepY=2.*I3Units.m,
                           StepZ=2.*I3Units.m,
                           StepZenith=0.,
                           StepAzimuth=0.,
                           StepT=5.*I3Units.ns,
                           ShowerSpacing=1.*I3Units.m,
                           MuonSpacing=0,
                           Boundary=700*I3Units.m)
        if seed is not None:
            logger.debug('Updating StepXYZ')
            Millipede.UpdateStepXYZ(coars_steps, seed.dir, 15*I3Units.m)
            Millipede.UpdateStepXYZ(finer_steps, seed.dir, 3*I3Units.m)
        tray.AddService('MuMillipedeParametrizationFactory', 'coarseSteps', **coars_steps)

        tray.AddService('I3BasicSeedServiceFactory', 'vetoseed',
            FirstGuesses=[f'{cfg.OUTPUT_PARTICLE_NAME}'],
            TimeShiftType='TNone',
            PositionShiftType='None')

        tray.Add('I3SimpleFitter',
            OutputName='MillipedeStarting1stPass_simplex',
            SeedService='vetoseed',
            Parametrization='coarseSteps',
            LogLikelihood='millipedellh',
            Minimizer='isimplex')

        tray.AddService('I3BasicSeedServiceFactory', 'firstsimplexseed',
                        FirstGuesses=['MillipedeStarting1stPass_simplex'],
                        TimeShiftType='TNone',
                        PositionShiftType='None')

        tray.Add('I3SimpleFitter',
             SeedService='firstsimplexseed',
             OutputName='MillipedeStarting1stPass',
             Parametrization='coarseSteps',
             LogLikelihood='millipedellh',
             Minimizer='imigrad')
        def notify1(frame):
            logger.debug(f"1st pass done! {datetime.datetime.now()}")
            logger.debug(f"MillipedeStarting1stPass: {frame['MillipedeStarting1stPass']}")

        tray.AddModule(notify1, "notify1")

        tray.AddService('MuMillipedeParametrizationFactory', 'fineSteps', **finer_steps)

        tray.AddService('I3BasicSeedServiceFactory', 'firstFitSeed',
            FirstGuess='MillipedeStarting1stPass',
            TimeShiftType='TNone',
            PositionShiftType='None')

        tray.Add('I3SimpleFitter',
             SeedService='firstFitSeed',
             OutputName='MillipedeStarting2ndPass_simplex',
             Parametrization='fineSteps',
             LogLikelihood='millipedellh',
             Minimizer='isimplex')

        tray.AddService('I3BasicSeedServiceFactory', 'secondsimplexseed',
                        FirstGuesses=['MillipedeStarting2ndPass_simplex'],
                        TimeShiftType='TNone',
                        PositionShiftType='None')

        tray.AddModule('I3SimpleFitter', 'MillipedeStarting2ndPass',
            OutputName='MillipedeStarting2ndPass',
            SeedService='firstFitSeed',
            Parametrization='fineSteps',
            LogLikelihood='millipedellh',
            Minimizer='imigrad')

        def notify2(frame):
            logger.debug(f"2nd pass done! {datetime.datetime.now()}")
            logger.debug(f"MillipedeStarting2ndPass: {frame['MillipedeStarting2ndPass']}")

        tray.AddModule(notify2, "notify2")

    @staticmethod
    def UpdateStepXYZ(the_steps, direction, uniform_step=15*I3Units.m):
        the_steps[f'StepX'] = numpy.sqrt(1-direction.x**2)*uniform_step
        the_steps[f'StepY'] = numpy.sqrt(1-direction.y**2)*uniform_step
        the_steps[f'StepZ'] = numpy.sqrt(1-direction.z**2)*uniform_step

    @staticmethod
    def to_pixelreco(frame: I3Frame, geometry: I3Frame) -> PixelReco:
        # Calculate reco losses, based on load_scan_state()
        reco_losses_inside, reco_losses_total = Millipede.get_reco_losses_inside(
            p_frame=frame, g_frame=geometry,
        )

        if "MillipedeStarting2ndPass_millipedellh" not in frame:
            llh = float("nan")
        else:
            llh = frame["MillipedeStarting2ndPass_millipedellh"].logl
        return PixelReco(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel=frame[cfg.I3FRAME_PIXEL].value,
            llh=llh,
            reco_losses_inside=reco_losses_inside,
            reco_losses_total=reco_losses_total,
            pos_var_index=frame[cfg.I3FRAME_POSVAR].value,
            position=frame["MillipedeStarting2ndPass"].pos,
            time=frame["MillipedeStarting2ndPass"].time,
            energy=frame["MillipedeStarting2ndPass"].energy,
        )

    @staticmethod
    def get_reco_losses_inside(p_frame: I3Frame, g_frame: I3Frame) -> Tuple[float, float]:

        if "MillipedeStarting2ndPass" not in p_frame:
            return numpy.nan, numpy.nan
        recoParticle = p_frame["MillipedeStarting2ndPass"]

        if "MillipedeStarting2ndPassParams" not in p_frame:
            return numpy.nan, numpy.nan

        def getRecoLosses(vecParticles):
            losses = []
            for p in vecParticles:
                if not p.is_cascade:
                    continue
                if p.energy == 0.:
                    continue
                losses.append([p.time, p.energy])
            return losses
        recoLosses = getRecoLosses(p_frame["MillipedeStarting2ndPassParams"])


        intersectionPoints = VHESelfVeto.IntersectionsWithInstrumentedVolume(g_frame["I3Geometry"], recoParticle)
        intersectionTimes = []
        for intersectionPoint in intersectionPoints:
            vecX = intersectionPoint.x - recoParticle.pos.x
            vecY = intersectionPoint.y - recoParticle.pos.y
            vecZ = intersectionPoint.z - recoParticle.pos.z

            prod = vecX*recoParticle.dir.x + vecY*recoParticle.dir.y + vecZ*recoParticle.dir.z
            dist = numpy.sqrt(vecX**2 + vecY**2 + vecZ**2)
            if prod < 0.:
                dist *= -1.
            intersectionTimes.append(dist/dataclasses.I3Constants.c + recoParticle.time)

        entryTime = None
        exitTime = None
        intersectionTimes = sorted(intersectionTimes)
        if len(intersectionTimes) == 0:
            return 0., 0.

        entryTime = intersectionTimes[0]-60.*I3Units.m/dataclasses.I3Constants.c
        intersectionTimes = intersectionTimes[1:]
        exitTime = intersectionTimes[-1]+60.*I3Units.m/dataclasses.I3Constants.c
        intersectionTimes = intersectionTimes[:-1]

        totalRecoLosses = 0.
        totalRecoLossesInside = 0.
        for entry in recoLosses:
            totalRecoLosses += entry[1]
            if entryTime is not None and entry[0] < entryTime:
                continue
            if exitTime is not None and entry[0] > exitTime:
                continue
            totalRecoLossesInside += entry[1]

        return totalRecoLossesInside, totalRecoLosses
