"""IceTray segment for a dummy reco."""


import datetime
import numpy as np
from typing import Final


from icecube.icetray import I3Units  # type: ignore[import]

# NOTE: icecube module imports are required to make IceTray modules and services available.
from icecube import (  # type: ignore[import]  # noqa: F401
    dataclasses,
    DomTools,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    lilliput,
    mue,
    spline_reco,
    photonics_service,
    recclasses,
    simclasses,
    STTools,
    VHESelfVeto,
)

# Class bindings directly accessed by the python code are imported explicitly.
from icecube.icetray import I3Frame, traysegment  # type: ignore[import]
from icecube.lilliput import scipymin  # type: ignore[import]
from icecube.photonics_service import I3PhotoSplineService  # type: ignore[import]
from icecube.STTools.seededRT.configuration_services import I3DOMLinkSeededRTConfigurationService  # type: ignore[import]

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from . import RecoInterface, VertexGenerator
from .common.pulse_proc import mask_deepcore


class SplineMPE(RecoInterface):
    """Logic for SplineMPE reco."""

    rt_cleaned_pulseseries = "SplitRTCleanedInIcePulses"
    cleaned_muon_pulseseries = "CleanedMuonPulses"
    cleaned_muon_pulseseries_ic = "CleanedMuonPulsesIC"

    MIE_BAREMU_PROB = "InfBareMu_mie_prob_z20a10_V2.fits"
    MIE_BAREMU_ABS = "InfBareMu_mie_abs_z20a10_V2.fits"
    MIE_STOCH_PROB = "InfHighEStoch_mie_prob_z20a10.fits"
    MIE_STOCH_ABS = "InfHighEStoch_mie_abs_z20a10.fits"

    SPLINE_REQUIREMENTS = [
        MIE_BAREMU_PROB,
        MIE_BAREMU_ABS,
        MIE_STOCH_PROB,
        MIE_STOCH_ABS,
    ]

    # Names used in the reco.
    energy_reco_seed = "OnlineL2_BestFit"
    energy_estimator = "OnlineL2_BestFit_MuEx"

    def __init__(self, realtime_format_version: str):
        super().__init__(realtime_format_version)
        # Mandatory attributes (RecoInterface).
        self.rotate_vertex = True
        self.refine_time = True
        self.add_fallback_position = True
        self.base_pulseseries = self.get_input_pulses(realtime_format_version)

        # Pick out the L2 SplineMPE online reco
        self.l2_splinempe = cfg.INPUT_KEY_NAMES_MAP.get(
            realtime_format_version,
            cfg.DEFAULT_INPUT_KEY_NAMES).l2_splinempe

        # This may be configurable in the future.
        # "VHESelfVeto" yields a reco-independent vertex seed.
        # Setting this to self.l2_splinempe
        # picks the output of the L2 SplineMPE reco
        # and is mostly supported for legacy reasons.
        self.vertex_seed_source = "VHESelfVeto"

    @staticmethod
    def get_prejitter(config="max") -> int:
        return 2 if config == "max" else 4

    @staticmethod
    def get_noise_model(config="max"):
        return "SRT" if config == "max" else "none"

    @staticmethod
    def get_postjitter(config="max"):
        return 2 if config == "max" else 0

    @staticmethod
    def get_KS_confidence_level(do_KS=False):
        return 5 if do_KS else 0

    @staticmethod
    def get_energy_dependent_jitter(config="max"):
        return True if config == "max" else False

    @staticmethod
    def get_energy_dependent_MPE(config="max"):
        return True if config == "max" else False

    @staticmethod
    def get_simplex_max_iterations():
        return 100

    @staticmethod
    def get_steps():
        vertex_step = 20 * I3Units.m
        vertex_bound = 2000 * I3Units.m
        vertex_bounds = [-vertex_bound, +vertex_bound]

        ## Time an vertex are degenerate.
        ## No minimization over time.
        # time_bound = 500 * I3Units.ns
        # time_bounds = [-time_bound, +time_bound]

        steps = dict(
            StepX=vertex_step,
            StepY=vertex_step,
            StepZ=vertex_step,
            BoundsX=vertex_bounds,
            BoundsY=vertex_bounds,
            BoundsZ=vertex_bounds,
            ## Time an vertex are degenerate.
            ## No minimization over time.
            # StepT=1.0 * I3Units.ns,
            # BoundsT=time_bounds,
        )

        return steps

    @traysegment
    def prepare_frames(self, tray, name: str, logger) -> None:
        # =========================================================
        # PULSE CLEANING
        # From "SplitUncleanedInIcePulses" to "CleanedMuonPulses".
        # "CleanedMuonPulses" is equivalent to "OnlineL2_CleanedMuonPulses".
        # =========================================================
        def checkName(frame: I3Frame, name: str) -> None:
            if name not in frame:
                raise RuntimeError(f"{name} not in frame.")
            else:
                logger.debug(f"Check that {name} is in frame: -> success.")

        # from icetray/filterscripts/python/all_filters.py
        seededRTConfig = I3DOMLinkSeededRTConfigurationService(
            # RT = Radius and Time
            ic_ic_RTRadius=150.0 * I3Units.m,
            ic_ic_RTTime=1000.0 * I3Units.ns,
            treat_string_36_as_deepcore=False,
            useDustlayerCorrection=False,
            allowSelfCoincidence=True,
        )

        # from icetray/filterscripts/python/baseproc.py
        tray.AddModule(
            "I3SeededRTCleaning_RecoPulseMask_Module",
            "BaseProc_RTCleaning",
            InputHitSeriesMapName=self.base_pulseseries,
            OutputHitSeriesMapName=self.rt_cleaned_pulseseries,
            STConfigService=seededRTConfig,
            SeedProcedure="HLCCoreHits",
            NHitsThreshold=2,
            MaxNIterations=3,
            Streams=[I3Frame.Physics],
        )

        tray.Add(checkName, name=self.rt_cleaned_pulseseries)

        # from icetray/filterscripts/python/baseproc.py
        tray.AddModule(
            "I3TimeWindowCleaning<I3RecoPulse>",
            "BaseProc_TimeWindowCleaning",
            InputResponse=self.rt_cleaned_pulseseries,
            OutputResponse=self.cleaned_muon_pulseseries,
            TimeWindow=6000 * I3Units.ns,
        )

        tray.Add(checkName, name=self.cleaned_muon_pulseseries)

        # =========================================================
        # ENERGY ESTIMATOR SEEDING
        # Provide SplineMPE with energy estimation from MuEx
        # This should improve the following SplineMPE track reco.
        # =========================================================
        def notify_muex(frame):
            logger.debug(f"Running MuEX - {datetime.datetime.now()}")

        tray.Add(notify_muex, "notify_muex")

        def log_frame(frame):
            logger.debug(f"{repr(frame)}/{frame}")

        tray.Add("Copy",
                 Keys=["l2_online_BestFit", self.energy_reco_seed],
                 If=lambda f: f.Has("l2_online_BestFit") and not f.Has(self.energy_reco_seed))

        # From icetray/filterscript/python/onlinel2filter.py
        tray.AddModule(
            "muex",
            self.energy_estimator,
            pulses=self.cleaned_muon_pulseseries,
            rectrk=self.energy_reco_seed,
            result=self.energy_estimator,
            energy=True,
            detail=True,
            compat=False,
            lcspan=0,
            If=lambda f: True,
        )
        tray.Add(log_frame, "logframe")

        tray.Add(
            mask_deepcore,
            origpulses=self.cleaned_muon_pulseseries,
            maskedpulses=self.cleaned_muon_pulseseries_ic,
        )

        ####

        if self.vertex_seed_source == "VHESelfVeto":
            # For HESE events, HESE_VHESelfVeto should already be in the frame.
            #   Here, we re-run the module nevertheless to ensure consistency
            #   in the settings of the scan regardless of the input event.

            tray.AddModule(
                "VHESelfVeto",
                "selfveto",
                VertexThreshold=250,
                Pulses=self.base_pulseseries + "HLC",
                OutputBool="VHESelfVeto",
                OutputVertexTime=cfg.INPUT_TIME_NAME,
                OutputVertexPos=cfg.INPUT_POS_NAME,
            )

            # this only runs if the previous module did not return anything
            tray.AddModule(
                "VHESelfVeto",
                "selfveto-emergency-lowen-settings",
                VertexThreshold=5,
                Pulses=self.base_pulseseries + "HLC",
                OutputBool="VHESelfVeto-seed-source",
                OutputVertexTime=cfg.INPUT_TIME_NAME,
                OutputVertexPos=cfg.INPUT_POS_NAME,
                If=lambda frame: not frame.Has("VHESelfVeto"),
            )

            def notify_seed(frame):
                logger.debug(f"Seed from {self.vertex_seed_source}:")
                logger.debug(frame[cfg.INPUT_POS_NAME])

            tray.Add(notify_seed)

        elif self.vertex_seed_source == self.l2_splinempe:
            # First vertex seed is extracted from OnlineL2 reco.
            def extract_seed(frame):
                seed_source = self.vertex_seed_source
                frame[cfg.INPUT_POS_NAME] = frame[seed_source].pos
                frame[cfg.INPUT_TIME_NAME] = dataclasses.I3Double(
                    frame[seed_source].time
                )

            tray.Add(extract_seed, "ExtractSeedInformation")

    def get_vertex_variations(self):
        return VertexGenerator.cylinder()

    def setup_reco(self) -> None:
        datastager = self.get_datastager()

        datastager.stage_files(self.SPLINE_REQUIREMENTS)

        BareMuTimingSpline: str = datastager.get_filepath(self.MIE_BAREMU_PROB)
        BareMuAmplitudeSpline: str = datastager.get_filepath(self.MIE_BAREMU_ABS)
        StochTimingSpline: str = datastager.get_filepath(self.MIE_STOCH_PROB)
        StochAmplitudeSpline: str = datastager.get_filepath(self.MIE_STOCH_ABS)

        self.bare_mu_spline = I3PhotoSplineService(
            BareMuAmplitudeSpline,
            BareMuTimingSpline,
            timingSigma=self.get_prejitter(),
        )
        self.stoch_spline = I3PhotoSplineService(
            StochAmplitudeSpline,
            StochTimingSpline,
            timingSigma=self.get_prejitter(),
        )
        self.noise_spline = I3PhotoSplineService(
            BareMuAmplitudeSpline,
            BareMuTimingSpline,
            timingSigma=1000,
        )

    @traysegment
    def traysegment(self, tray, name, logger, **kwargs):
        """SplineMPE reco"""

        def checkName(frame: I3Frame, name: str) -> None:
            if name not in frame:
                raise RuntimeError(f"{name} not in frame.")
            else:
                logger.debug(f"Check that {name} is in frame: -> success.")

        vertex_seed = cfg.OUTPUT_PARTICLE_NAME

        # Notify start.
        def notify0(frame):
            logger.debug(
                f"starting a new SplineMPE fit ({name})! {datetime.datetime.now()}"
            )

        tray.Add(notify0, "notify0")

        # Check that the base pulses are in the input frame.
        tray.Add(checkName, name=self.base_pulseseries)

        tray.AddModule(checkName, name=self.energy_reco_seed)

        # ==============================================================================
        # MAIN RECONSTRUCTION
        # Default configuration takes from SplineMPE "max"
        # Multiple energy estimators can be provided but they should be run beforehand.
        # =============================================================================

        tray.AddModule(checkName, name=self.energy_estimator)

        tray.Add(
            "I3SplineRecoLikelihoodFactory",
            "splinempe-llh",
            PhotonicsService=self.bare_mu_spline,
            PhotonicsServiceStochastics=self.stoch_spline,
            PhotonicsServiceRandomNoise=self.noise_spline,
            ModelStochastics=False,
            NoiseModel=self.get_noise_model(),
            Pulses=self.cleaned_muon_pulseseries_ic,
            E_Estimators=[self.energy_estimator],
            Likelihood="MPE",
            NoiseRate=10 * I3Units.hertz,
            PreJitter=0,
            PostJitter=self.get_postjitter(),
            KSConfidenceLevel=self.get_KS_confidence_level(do_KS=False),
            ChargeCalcStep=0,
            CutMode="late",
            EnergyDependentJitter=self.get_energy_dependent_jitter(),
            EnergyDependentMPE=self.get_energy_dependent_MPE(),
        )

        # simplex should be the default
        # note that IMinuitMinimizer also provides a simplex algorithm
        tray.context["simplex"] = scipymin.SciPyMinimizer(
            name="scipy_simplex_f",
            method="Nelder-Mead",
            tolerance=0.1,  # this was parameterized in the original code
            max_iterations=self.get_simplex_max_iterations(),
        )

        # Alternative minimizer.
        # tray.context["iminuit"] = i3minuit.IMinuitMinimizer(
        #     name="iminuit",
        #     Tolerance=10,
        #     MaxIterations=1000,
        #     MinuitStrategy=2,
        #     MinuitPrintLevel=0,
        # )

        # parametrization for minimization
        steps = self.get_steps()
        tray.Add(
            "I3SimpleParametrizationFactory",
            "splinempe-param",
            **steps,
        )

        tray.Add(checkName, name=vertex_seed)

        if self.add_fallback_position:
            tray.AddService(
                "I3BasicSeedServiceFactory",
                "splinempe-seed",
                FirstGuesses=[
                    vertex_seed,
                    f"{vertex_seed}_fallback",
                ],
                TimeShiftType="TNone",
                PositionShiftType="None",
            )
        else:
            tray.Add(
                "I3BasicSeedServiceFactory",
                "splinempe-seed",
                FirstGuess=vertex_seed,
                TimeShiftType="TNone",
                PositionShiftType="None",
            )

        tray.Add(
            "I3SimpleFitter",
            OutputName="splinempe-reco",
            SeedService="splinempe-seed",
            Parametrization="splinempe-param",
            LogLikelihood="splinempe-llh",
            Minimizer="simplex",
        )

        tray.Add(checkName, name="splinempe-reco" + "FitParams")

        def notify1(frame):
            logger.debug(f"SplineMPE pass done! {datetime.datetime.now()}")

        tray.Add(notify1, "notify1")

    @classmethod
    def to_recopixelvariation(
        cls, frame: I3Frame, geometry: I3Frame
    ) -> RecoPixelVariation:
        return RecoPixelVariation(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel_id=frame[cfg.I3FRAME_PIXEL].value,
            llh=frame[
                "splinempe-reco" + "FitParams"
            ].logl,  # FitParams is hardcoded (where?)
            reco_losses_inside=np.NaN,
            reco_losses_total=np.NaN,
            posvar_id=frame[cfg.I3FRAME_POSVAR].value,
            position=frame["splinempe-reco"].pos,
            time=frame["splinempe-reco"].time,
            energy=frame["splinempe-reco"].energy,
        )

RECO_CLASS: Final[type[RecoInterface]] = SplineMPE
