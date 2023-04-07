"""IceTray segment for a millipede reco."""

# fmt: off
# pylint: skip-file
# mypy: ignore-errors

import copy
import datetime
import os
from typing import Tuple

import numpy
from I3Tray import I3Units
from icecube import (  # noqa: F401
    VHESelfVeto,
    dataclasses,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    lilliput,
    millipede,
    photonics_service,
    recclasses,
    simclasses,
)
from icecube.icetray import I3Frame

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from . import RecoInterface


class MillipedeOriginal(RecoInterface):
    """Reco logic for millipede."""
    # Constants ########################################################

    pulsesName = cfg.INPUT_PULSES_NAME
    pulsesName_cleaned = pulsesName+'LatePulseCleaned'
    SPEScale = 0.99

    # Load Data ########################################################

    # At HESE energies, deposited light is dominated by the stochastic losses
    # (muon part emits so little light in comparison)
    # This is why we can use cascade tables
    # _splinedir = os.path.expandvars("$I3_DATA/photon-tables/splines")
    filestager = dataio.get_stagers()

    _base = os.path.join(cfg.SPLINE_DATA_SOURCE, "ems_mie_z20_a10.%s.fits")
    # for fname in [_base % "abs", _base % "prob"]:
    #     if not os.path.exists(fname):
    #        raise FileNotFoundError(fname)
    cascade_service = photonics_service.I3PhotoSplineService(
        filestager.GetReadablePath(_base % "abs"), filestager.GetReadablePath(_base % "prob"), timingSigma=0.0
    )
    cascade_service.SetEfficiencies(SPEScale)
    muon_service = None

    def makeSurePulsesExist(frame, pulsesName) -> None:
        if pulsesName not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName + "TimeWindows" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName + "TimeWindows"))
        if pulsesName + "TimeRange" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName + "TimeRange"))

    @icetray.traysegment
    def exclusions(tray, name):
        tray.Add('Delete', keys=['BrightDOMs',
                                 'SaturatedDOMs',
                                 'DeepCoreDOMs',
                                 MillipedeOriginal.pulsesName_cleaned,
                                 MillipedeOriginal.pulsesName_cleaned+'TimeWindows',
                                 MillipedeOriginal.pulsesName_cleaned+'TimeRange'])

        exclusionList = \
        tray.AddSegment(millipede.HighEnergyExclusions, 'millipede_DOM_exclusions',
            Pulses = MillipedeOriginal.pulsesName,
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
                       ListNames = ["BrightDOMs"])
        # exclude bright DOMs
        ExcludedDOMs = exclusionList

        ##################

        def _weighted_quantile_arg(values, weights, q=0.5):
            indices = numpy.argsort(values)
            sorted_indices = numpy.arange(len(values))[indices]
            medianidx = (weights[indices].cumsum()/weights[indices].sum()).searchsorted(q)
            if (0 <= medianidx) and (medianidx < len(values)):
                return sorted_indices[medianidx]
            else:
                return numpy.nan

        def weighted_quantile(values, weights, q=0.5):
            if len(values) != len(weights):
                raise ValueError("shape of `values` and `weights` don't match!")
            index = _weighted_quantile_arg(values, weights, q=q)
            if not numpy.isnan(index):
                return values[index]
            else:
                return numpy.nan

        def weighted_median(values, weights):
            return weighted_quantile(values, weights, q=0.5)

        def LatePulseCleaning(frame, Pulses, Residual=3e3*I3Units.ns):
            pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, Pulses)
            mask = dataclasses.I3RecoPulseSeriesMapMask(frame, Pulses)
            counter, charge = 0, 0
            qtot = 0
            times = dataclasses.I3TimeWindowSeriesMap()
            for omkey, ps in pulses.items():
                if len(ps) < 2:
                    if len(ps) == 1:
                        qtot += ps[0].charge
                    continue
                ts = numpy.asarray([p.time for p in ps])
                cs = numpy.asarray([p.charge for p in ps])
                median = weighted_median(ts, cs)
                qtot += cs.sum()
                for p in ps:
                    if p.time >= (median+Residual):
                        if omkey not in times:
                            ts = dataclasses.I3TimeWindowSeries()
                            ts.append(dataclasses.I3TimeWindow(median+Residual, numpy.inf)) # this defines the **excluded** time window
                            times[omkey] = ts
                        mask.set(omkey, p, False)
                        counter += 1
                        charge += p.charge
            frame[MillipedeOriginal.pulsesName_cleaned] = mask
            frame[MillipedeOriginal.pulsesName_cleaned+"TimeWindows"] = times
            frame[MillipedeOriginal.pulsesName_cleaned+"TimeRange"] = copy.deepcopy(frame[Pulses+"TimeRange"])

        tray.AddModule(LatePulseCleaning, "LatePulseCleaning",
                       Pulses=MillipedeOriginal.pulsesName,
                       )
        return ExcludedDOMs + [MillipedeOriginal.pulsesName_cleaned+'TimeWindows']


    @icetray.traysegment
    def traysegment(tray, name, logger, seed=None):
        """Perform MillipedeOriginal reco."""
        ExcludedDOMs = tray.Add(MillipedeOriginal.exclusions)

        tray.Add(MillipedeOriginal.makeSurePulsesExist, pulsesName=MillipedeOriginal.pulsesName_cleaned)

        def notify0(frame):
            logger.debug(f"starting a new fit ({name})! {datetime.datetime.now()}")

        tray.AddModule(notify0, "notify0")

        tray.AddService('MillipedeLikelihoodFactory', 'millipedellh',
            MuonPhotonicsService=MillipedeOriginal.muon_service,
            CascadePhotonicsService=MillipedeOriginal.cascade_service,
            ShowerRegularization=0,
            PhotonsPerBin=15,
            # DOMEfficiency=SPEScale, # moved to cascade_service.SetEfficiencies(SPEScale)
            ExcludedDOMs=ExcludedDOMs,
            PartialExclusion=True,
            ReadoutWindow=MillipedeOriginal.pulsesName_cleaned+'TimeRange',
            Pulses=MillipedeOriginal.pulsesName_cleaned,
            BinSigma=3)

        tray.AddService('I3GSLRandomServiceFactory','I3RandomService')

        tray.AddService('I3GSLSimplexFactory', 'simplex',
            MaxIterations=20000)

        coars_steps = dict(StepX=10.*I3Units.m,
                           StepY=10.*I3Units.m,
                           StepZ=10.*I3Units.m,
                           StepZenith=0.,
                           StepAzimuth=0.,
                           StepT=0.*I3Units.ns,
                           ShowerSpacing=5.*I3Units.m,
                           MuonSpacing=0)

        finer_steps = dict(StepX=2.*I3Units.m,
                           StepY=2.*I3Units.m,
                           StepZ=2.*I3Units.m,
                           StepZenith=0.,
                           StepAzimuth=0.,
                           StepT=5.*I3Units.ns,
                           ShowerSpacing=2.5*I3Units.m,
                           MuonSpacing=0)

        tray.AddService('MuMillipedeParametrizationFactory', 'coarseSteps', **coars_steps)

        tray.AddService('I3BasicSeedServiceFactory', 'vetoseed',
            FirstGuesses=[f'{cfg.OUTPUT_PARTICLE_NAME}'],
            TimeShiftType='TNone',
            PositionShiftType='None')

        tray.Add('I3SimpleFitter',
            OutputName='MillipedeStarting1stPass',
            SeedService='vetoseed',
            Parametrization='coarseSteps',
            LogLikelihood='millipedellh',
            Minimizer='simplex')

        def notify1(frame):
            logger.debug(f"1st pass done! {datetime.datetime.now()}")
            logger.debug(f"Seeded with: {frame[f'{cfg.OUTPUT_PARTICLE_NAME}']}")
            logger.debug(f"MillipedeStarting1stPass: {frame['MillipedeStarting1stPass']}")

        tray.AddModule(notify1, "notify1")

        tray.AddService('MuMillipedeParametrizationFactory', 'fineSteps', **finer_steps)

        tray.AddService('I3BasicSeedServiceFactory', 'firstFitSeed',
            FirstGuesses=['MillipedeStarting1stPass'],
            TimeShiftType='TNone',
            PositionShiftType='None')

        tray.Add('I3SimpleFitter',
             SeedService='firstFitSeed',
             OutputName='MillipedeStarting2ndPass',
             Parametrization='fineSteps',
             LogLikelihood='millipedellh',
             Minimizer='simplex')

        def notify2(frame):
            logger.debug(f"2nd pass done! {datetime.datetime.now()}")
            logger.debug(f"MillipedeStarting2ndPass: {frame['MillipedeStarting2ndPass']}")

        tray.AddModule(notify2, "notify2")

    @staticmethod
    def to_recopixelvariation(frame: I3Frame, geometry: I3Frame) -> RecoPixelVariation:
        # Calculate reco losses, based on load_scan_state()
        reco_losses_inside, reco_losses_total = MillipedeOriginal.get_reco_losses_inside(
            p_frame=frame, g_frame=geometry,
        )

        if "MillipedeStarting2ndPass_millipedellh" not in frame:
            llh = float("nan")
        else:
            llh = frame["MillipedeStarting2ndPass_millipedellh"].logl
        return RecoPixelVariation(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel_id=frame[cfg.I3FRAME_PIXEL].value,
            llh=llh,
            reco_losses_inside=reco_losses_inside,
            reco_losses_total=reco_losses_total,
            posvar_id=frame[cfg.I3FRAME_POSVAR].value,
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
