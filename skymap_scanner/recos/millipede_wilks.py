"""IceTray segment for a millipede reco."""

# fmt: off
# pylint: skip-file
# mypy: ignore-errors

import datetime
import os
from typing import Final, List, Tuple

import numpy
from icecube.icetray import I3Units
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
    simclasses
)
from icecube.icetray import I3Frame

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from . import RecoInterface, VertexGenerator
from .common.pulse_proc import mask_deepcore, pulse_cleaning


class MillipedeWilks(RecoInterface):
    """Reco logic for millipede."""

    # Spline requirements ##############################################
    FTP_ABS_SPLINE = "cascade_single_spice_ftp-v1_flat_z20_a5.abs.fits"
    FTP_PROB_SPLINE = "cascade_single_spice_ftp-v1_flat_z20_a5.prob.v2.fits"
    FTP_EFFD_SPLINE = "cascade_effectivedistance_spice_ftp-v1_z20.eff.fits"
    FTP_EFFP_SPLINE = "cascade_effectivedistance_spice_ftp-v1_z20.prob.fits"
    FTP_TMOD_SPLINE = "cascade_effectivedistance_spice_ftp-v1_z20.tmod.fits"

    SPLINE_REQUIREMENTS = [FTP_ABS_SPLINE, FTP_PROB_SPLINE, FTP_EFFD_SPLINE,
                           FTP_EFFP_SPLINE, FTP_TMOD_SPLINE]

    def __init__(self, realtime_format_version: str):
        super().__init__(realtime_format_version)
        self.rotate_vertex = True
        self.refine_time = True
        self.add_fallback_position = True

        self.pulsesName_input = self.get_input_pulses(realtime_format_version)
        self.pulsesName = self.pulsesName_input + "IC"
        self.pulsesName_cleaned = self.pulsesName+'LatePulseCleaned'



    @staticmethod
    def get_vertex_variations() -> List[dataclasses.I3Position]:
        """Returns a list of vectors referenced to the origin that will be used to generate the vertex position variations.
        """
        return VertexGenerator.point()

    def setup_reco(self):
        datastager = self.get_datastager()

        datastager.stage_files(self.SPLINE_REQUIREMENTS)

        abs_spline: str = datastager.get_filepath(self.FTP_ABS_SPLINE)
        prob_spline: str = datastager.get_filepath(self.FTP_PROB_SPLINE)
        effd_spline: str = datastager.get_filepath(self.FTP_EFFD_SPLINE)
        effp_spline: str = datastager.get_filepath(self.FTP_EFFP_SPLINE)
        tmod_spline: str = datastager.get_filepath(self.FTP_TMOD_SPLINE)

        self.cascade_service = photonics_service.I3PhotoSplineService(
            abs_spline, prob_spline, timingSigma=0.0,
            effectivedistancetable = effd_spline,
            tiltTableDir = os.path.expandvars('$I3_BUILD/ice-models/resources/models/ICEMODEL/spice_ftp-v1/'),
            quantileEpsilon=1,
            effectivedistancetableprob = effp_spline,
            effectivedistancetabletmod = tmod_spline
        )

        self.muon_service = None

    @icetray.traysegment
    def prepare_frames(self, tray, name, logger):
        # Generates the vertex seed for the initial scan.
        # Only run if HESE_VHESelfVeto is not present in the frame.
        # VertexThreshold is 250 in the original HESE analysis (Tianlu)
        # If HESE_VHESelfVeto is already in the frame, is likely using implicitly a VertexThreshold of 250 already. To be determined when this is not the case.
        def extract_seed(frame):
            seed_prefix = "HESE_VHESelfVeto"
            frame[cfg.INPUT_POS_NAME] = frame[seed_prefix + "VertexPos"]
            frame[cfg.INPUT_TIME_NAME] = frame[seed_prefix + "VertexTime"]

        tray.Add(extract_seed, "ExtractSeed",
                 If = lambda frame: frame.Has("HESE_VHESelfVeto"))

        tray.AddModule('VHESelfVeto', 'selfveto',
            VertexThreshold=250,
            Pulses=self.pulsesName_input+'HLC',
            OutputBool='HESE_VHESelfVeto',
            OutputVertexTime=cfg.INPUT_TIME_NAME,
            OutputVertexPos=cfg.INPUT_POS_NAME,
            If=lambda frame: "HESE_VHESelfVeto" not in frame)

        # this only runs if the previous module did not return anything
        tray.AddModule('VHESelfVeto', 'selfveto-emergency-lowen-settings',
                       VertexThreshold=5,
                       Pulses=self.pulsesName_input+'HLC',
                       OutputBool='VHESelfVeto_meaningless_lowen',
                       OutputVertexTime=cfg.INPUT_TIME_NAME,
                       OutputVertexPos=cfg.INPUT_POS_NAME,
                       If=lambda frame: not frame.Has("HESE_VHESelfVeto"))

        tray.Add(mask_deepcore, origpulses=self.pulsesName_input, maskedpulses=self.pulsesName)

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
            BrightDOMThreshold=2,
            BadDomsList='BadDomsList',
            CalibrationErrata='CalibrationErrata',
            SaturationWindows='SaturationWindows'
            )


        # I like having frame objects in there even if they are empty for some frames
        def createEmptyDOMLists(frame, ListNames=[]):
            for name in ListNames:
                if name in frame:
                    continue
                frame[name] = dataclasses.I3VectorOMKey()
        tray.AddModule(createEmptyDOMLists, 'createEmptyDOMLists',
                       ListNames = ["BrightDOMs"])
        # exclude bright DOMs
        ExcludedDOMs = exclusionList

        def skipunhits(frame, output, pulses):
            keepstrings = [1,3,5,14,16,18,20,31,33,35,37,39,51,53,55,57,59,68,70,72,74]
            keepoms = list(range(1,60,5))
            all_pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(
                frame, pulses)
            omgeo = frame['I3Geometry']
            geo = omgeo.omgeo
            unhits = dataclasses.I3VectorOMKey()
            for k, v in geo.items():
                if v.omtype != dataclasses.I3OMGeo.OMType.IceCube:
                    continue
                if k.string not in keepstrings:
                    if k not in all_pulses.keys():
                        unhits.append(k)
                else:
                    if k not in all_pulses.keys() and k.om not in keepoms:
                        unhits.append(k)

            frame[output] = unhits

        ##################
        tray.AddModule(pulse_cleaning, "LatePulseCleaning",
                       input_pulses_name=self.pulsesName,
                       output_pulses_name=self.pulsesName_cleaned,
                       residual=1.5e3*I3Units.ns)
        ExcludedDOMs.append(self.pulsesName_cleaned+'TimeWindows')

        tray.Add(skipunhits, output='OtherUnhits', pulses=self.pulsesName_cleaned)
        ExcludedDOMs.append('OtherUnhits')
        return ExcludedDOMs


    @icetray.traysegment
    def traysegment(self, tray, name, logger, seed=None):
        """Perform MillipedeWilks reco."""
        def check(frame):
            cal = frame['I3Calibration']
            omkeys = list(cal.dom_cal.keys())
            mean_spes = [dataclasses.mean_spe_charge(cal.dom_cal[_]) for _ in omkeys]
            logger.debug('Mean SPEs')
            for mean_spe, omkey in zip(mean_spes[::100], omkeys[::100]):
                x = cal.dom_cal[omkey]
                logger.debug(f'...{omkey}: {mean_spe} {x.Mean()} {x.mean_atwd_charge_corretion}')
                
        tray.Add(check)

        ExcludedDOMs = tray.Add(self.exclusions)

        tray.Add(self.makeSurePulsesExist, pulsesName=self.pulsesName_cleaned)

        def notify0(frame):
            logger.debug(f"starting a new fit ({name})! {datetime.datetime.now()}")

        tray.AddModule(notify0, "notify0")

        tray.AddService('MillipedeLikelihoodFactory', 'millipedellh',
            MuonPhotonicsService=self.muon_service,
            CascadePhotonicsService=self.cascade_service,
            ShowerRegularization=1e-14,
            ExcludedDOMs=ExcludedDOMs,
            PartialExclusion=True,
            ReadoutWindow=self.pulsesName_cleaned + 'TimeRange',
            Pulses=self.pulsesName_cleaned,
            BinSigma=2,
            MinTimeWidth=25,
            RelUncertainty=1)

        tray.AddService('I3GSLRandomServiceFactory', 'I3RandomService')

        tray.context['isimplex'] = lilliput.IMinuitMinimizer(
            MaxIterations=2000,
            Tolerance=0.01,
            Algorithm="SIMPLEX",
            MinuitPrintLevel=2,
            MinuitPrecision=numpy.finfo('float32').eps
        )
        tray.context['imigrad'] = lilliput.IMinuitMinimizer(
            MaxIterations=1000,
            Tolerance=0.01,
            Algorithm="MIGRAD",
            WithGradients=True,
            FlatnessCheck=False,
            IgnoreEDM=True, # Don't report convergence failures
            CheckGradient=False, # Don't die on gradient errors
            MinuitStrategy=0, # Don't try to check local curvature
            MinuitPrintLevel=2
            )

        coars_steps = dict(StepX=100.*I3Units.m,
                           StepY=100.*I3Units.m,
                           StepZ=100.*I3Units.m,
                           StepZenith=0.,
                           StepAzimuth=0.,
                           StepT=250.*I3Units.ns,
                           ShowerSpacing=5.*I3Units.m,
                           MuonSpacing=0,
                           Boundary=650*I3Units.m)
        finer_steps = dict(StepX=2.*I3Units.m,
                           StepY=2.*I3Units.m,
                           StepZ=2.*I3Units.m,
                           StepZenith=0.,
                           StepAzimuth=0.,
                           StepT=5.*I3Units.ns,
                           ShowerSpacing=2.5*I3Units.m,
                           MuonSpacing=0,
                           Boundary=650*I3Units.m)
        if seed is not None:
            logger.debug('Updating StepXYZ')
            self.UpdateStepXYZ(coars_steps, seed.dir, 150*I3Units.m)
            self.UpdateStepXYZ(finer_steps, seed.dir, 3*I3Units.m)
        tray.AddService('MuMillipedeParametrizationFactory', 'coarseSteps', **coars_steps)

        tray.AddService('I3BasicSeedServiceFactory', 'vetoseed',
            FirstGuesses=[f'{cfg.OUTPUT_PARTICLE_NAME}', f'{cfg.OUTPUT_PARTICLE_NAME}_fallback'],
            TimeShiftType='TNone',
            PositionShiftType='None')

        tray.Add('I3SimpleFitter',
            OutputName='MillipedeStarting1stPass',
            SeedService='vetoseed',
            Parametrization='coarseSteps',
            LogLikelihood='millipedellh',
            Minimizer='isimplex')

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
                 OutputName='MillipedeStarting2ndPass_simplex',
                 Parametrization='fineSteps',
                 LogLikelihood='millipedellh',
                 Minimizer='isimplex')

        tray.AddService('I3BasicSeedServiceFactory', 'secondsimplexseed',
            FirstGuesses=['MillipedeStarting2ndPass_simplex'],
            TimeShiftType='TNone',
            PositionShiftType='None')

        tray.Add('I3SimpleFitter',
             SeedService='secondsimplexseed',
             OutputName='MillipedeStarting2ndPass',
             Parametrization='fineSteps',
             LogLikelihood='millipedellh',
             Minimizer='imigrad')

        def notify2(frame):
            logger.debug(f"2nd pass done! {datetime.datetime.now()}")
            logger.debug(f"MillipedeStarting2ndPass: {frame['MillipedeStarting2ndPass']}")

        tray.AddModule(notify2, "notify2")

    @staticmethod
    def UpdateStepXYZ(the_steps, direction, uniform_step=15*I3Units.m):
        the_steps['StepX'] = numpy.sqrt(1-direction.x**2)*uniform_step
        the_steps['StepY'] = numpy.sqrt(1-direction.y**2)*uniform_step
        the_steps['StepZ'] = numpy.sqrt(1-direction.z**2)*uniform_step

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

RECO_CLASS: Final[type[RecoInterface]] = MillipedeWilks
