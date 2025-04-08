"""IceTray segment for a millipede reco."""

# fmt: off
# pylint: skip-file
# mypy: ignore-errors

import datetime
from typing import Final, List, Tuple

import numpy

from icecube.icetray import I3Units
from icecube import (  # noqa: F401
    VHESelfVeto,
    dataclasses,
    dataio,
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
from . import RecoInterface, VertexGenerator
from .common.pulse_proc import late_pulse_cleaning

class MillipedeOriginal(RecoInterface):
    """Reco logic for millipede."""

    @staticmethod
    def get_vertex_variations() -> List[dataclasses.I3Position]:
        """Returns a list of vectors referenced to the origin that will be used to generate the vertex position variations.
        """
        variation_distance = 20.*I3Units.m

        if cfg.ENV.SKYSCAN_MINI_TEST:
            return VertexGenerator.mini_test(variation_distance=variation_distance)
        else:    
            return VertexGenerator.octahedron(radius=variation_distance)

    # Spline requirements
    MIE_ABS_SPLINE = "ems_mie_z20_a10.abs.fits"
    MIE_PROB_SPLINE = "ems_mie_z20_a10.prob.fits"

    SPLINE_REQUIREMENTS = [ MIE_ABS_SPLINE, MIE_PROB_SPLINE ]

    # Constants ########################################################
    SPEScale = 0.99 # DOM efficiency

    # Load Data ########################################################
    # At HESE energies, deposited light is dominated by the stochastic losses
    # (muon part emits so little light in comparison)
    # This is why we can use cascade tables

    @icetray.traysegment
    def prepare_frames(self, tray, name, logger):
        # If VHESelfVeto is already present, copy over the output to the names used by Skymap Scanner  for seeding the vertices.
        def extract_seed(frame):
            seed_prefix = "HESE_VHESelfVeto"
            frame[cfg.INPUT_POS_NAME] = frame[seed_prefix + "VertexPos"]
            frame[cfg.INPUT_TIME_NAME] = frame[seed_prefix + "VertexTime"]

        tray.Add(extract_seed, "ExtractSeed",
                 If = lambda frame: frame.Has("HESE_VHESelfVeto"))
        
        # Generates the vertex seed for the initial scan. 
        # Only run if HESE_VHESelfVeto is not present in the frame.
        # VertexThreshold is 250 in the original HESE analysis (Tianlu)
        # If HESE_VHESelfVeto is already in the frame, is likely using implicitly a VertexThreshold of 250 already. To be determined when this is not the case.
        tray.AddModule('VHESelfVeto', 'selfveto',
                    VertexThreshold=2,
                    Pulses=self.pulsesName+'HLC',
                    OutputBool='HESE_VHESelfVeto',
                    OutputVertexTime=cfg.INPUT_TIME_NAME,
                    OutputVertexPos=cfg.INPUT_POS_NAME,
                    If=lambda frame: "HESE_VHESelfVeto" not in frame)

    def __init__(self, realtime_format_version: str):
        super().__init__(realtime_format_version)
        self.rotate_vertex = False
        self.refine_time = False
        self.add_fallback_position = False

        self.pulsesName = self.get_input_pulses(realtime_format_version)
        self.pulsesName_cleaned = self.pulsesName+'LatePulseCleaned'

    def setup_reco(self):
        datastager = self.get_datastager()

        datastager.stage_files(self.SPLINE_REQUIREMENTS)
        
        abs_spline = datastager.get_filepath(self.MIE_ABS_SPLINE)
        prob_spline = datastager.get_filepath(self.MIE_PROB_SPLINE)

        self.cascade_service = photonics_service.I3PhotoSplineService(abs_spline, prob_spline, timingSigma=0.0)

        self.cascade_service.SetEfficiencies(self.SPEScale)

        self.muon_service = None

    @staticmethod
    def makeSurePulsesExist(frame, pulsesName) -> None:
        if pulsesName not in frame:
            raise RuntimeError(f"{pulsesName} not in frame")
        if pulsesName + "TimeWindows" not in frame:
            raise RuntimeError(f"{pulsesName + 'TimeWindows'} not in frame")
        if pulsesName + "TimeRange" not in frame:
            raise RuntimeError(f"{pulsesName + 'TimeRange'} not in frame")

    @icetray.traysegment
    def exclusions(self, tray, name):
        tray.Add('Delete', keys=['BrightDOMs',
                                 'SaturatedDOMs',
                                 'DeepCoreDOMs',
                                 self.pulsesName_cleaned,
                                 self.pulsesName_cleaned+'TimeWindows',
                                 self.pulsesName_cleaned+'TimeRange'])

        exclusionList = \
        tray.AddSegment(millipede.HighEnergyExclusions, 'millipede_DOM_exclusions',
            Pulses = self.pulsesName,
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

        tray.AddModule(late_pulse_cleaning, "LatePulseCleaning",
                       input_pulses_name=self.pulsesName,
                       output_pulses_name=self.pulsesName_cleaned,
                       orig_pulses_name=self.pulsesName,
                       residual=1.5e3*I3Units.ns,
                       )
        return ExcludedDOMs + [self.pulsesName_cleaned+'TimeWindows']


    @icetray.traysegment
    def traysegment(self, tray, name, logger, seed=None):
        """Perform MillipedeOriginal reco."""

        ExcludedDOMs = tray.Add(self.exclusions)

        tray.Add(self.makeSurePulsesExist, pulsesName=self.pulsesName_cleaned)

        def notify0(frame):
            logger.debug(f"starting a new fit ({name})! {datetime.datetime.now()}")

        tray.AddModule(notify0, "notify0")

        tray.AddService('MillipedeLikelihoodFactory', 'millipedellh',
            MuonPhotonicsService=self.muon_service,
            CascadePhotonicsService=self.cascade_service,
            ShowerRegularization=0,
            PhotonsPerBin=15,
            ExcludedDOMs=ExcludedDOMs,
            PartialExclusion=True,
            ReadoutWindow=self.pulsesName_cleaned+'TimeRange',
            Pulses=self.pulsesName_cleaned,
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

    @classmethod
    def to_recopixelvariation(cls, frame: I3Frame, geometry: I3Frame) -> RecoPixelVariation:
        # Calculate reco losses, based on load_scan_state()
        reco_losses_inside, reco_losses_total = cls.get_reco_losses_inside(
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

# Provide a standard alias for the reconstruction class provided by this module.
RECO_CLASS: Final[type[RecoInterface]] = MillipedeOriginal
