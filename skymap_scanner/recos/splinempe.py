"""IceTray segment for a dummy reco."""


import datetime
import numpy as np
import os
from pathlib import Path
from typing import List


from I3Tray import I3Units  # type: ignore[import]

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
)

# Class bindings directly accessed by the python code are imported explicitly.
from icecube.icetray import I3Frame, traysegment  # type: ignore[import]
from icecube.lilliput import scipymin, i3minuit  # type: ignore[import]
from icecube.photonics_service import I3PhotoSplineService  # type: ignore[import]
from icecube.STTools.seededRT.configuration_services import I3DOMLinkSeededRTConfigurationService  # type: ignore[import]

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from ..utils.data_handling import DataStager
from . import RecoInterface

MIE_BAREMU_PROB = "InfBareMu_mie_prob_z20a10_V2.fits"
MIE_BAREMU_ABS = "InfBareMu_mie_abs_z20a10_V2.fits"
MIE_STOCH_PROB = "InfHighEStoch_mie_prob_z20a10.fits"
MIE_STOCH_ABS = "InfHighEStoch_mie_abs_z20a10.fits"

spline_requirements = [MIE_BAREMU_PROB, MIE_BAREMU_ABS, MIE_STOCH_PROB, MIE_STOCH_ABS]


class Splinempe(RecoInterface):
    """Logic for SplineMPE reco."""

    base_pulseseries = cfg.INPUT_PULSES_NAME
    rt_cleaned_pulseseries = "SplitRTCleanedInIcePulses"
    cleaned_muon_pulseseries = "CleanedMuonPulses"

    datastager = DataStager(
        local_paths=cfg.LOCAL_DATA_SOURCES,
        local_subdir=cfg.LOCAL_SPLINE_SUBDIR,
        remote_path=f"{cfg.REMOTE_DATA_SOURCE}/{cfg.REMOTE_SPLINE_SUBDIR}",
    )

    datastager.stage_files(spline_requirements)

    BareMuTimingSpline: str = datastager.get_filepath(MIE_BAREMU_PROB)
    BareMuAmplitudeSpline: str = datastager.get_filepath(MIE_BAREMU_ABS)
    StochTimingSpline: str = datastager.get_filepath(MIE_STOCH_PROB)
    StochAmplitudeSpline: str = datastager.get_filepath(MIE_STOCH_ABS)

    @staticmethod
    def get_prejitter(config="max") -> int:
        return 2 if config == "max" else 4

    @staticmethod
    def get_splines() -> (
        tuple[
            I3PhotoSplineService,
            I3PhotoSplineService,
            I3PhotoSplineService,
        ]
    ):
        bare_mu_spline = I3PhotoSplineService(
            Splinempe.BareMuAmplitudeSpline,
            Splinempe.BareMuTimingSpline,
            timingSigma=Splinempe.get_prejitter(),
        )
        stoch_spline = I3PhotoSplineService(
            Splinempe.StochAmplitudeSpline,
            Splinempe.StochTimingSpline,
            timingSigma=Splinempe.get_prejitter(),
        )
        noise_spline = I3PhotoSplineService(
            Splinempe.BareMuAmplitudeSpline,
            Splinempe.BareMuTimingSpline,
            timingSigma=1000,
        )
        return bare_mu_spline, stoch_spline, noise_spline

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
        time_bound = 500 * I3Units.ns
        time_bounds = [-time_bound, +time_bound]

        steps = dict(
            StepX=vertex_step,
            StepY=vertex_step,
            StepZ=vertex_step,
            BoundsX=vertex_bounds,
            BoundsY=vertex_bounds,
            BoundsZ=vertex_bounds,
            StepZenith=0.1 * I3Units.radian,
            StepAzimuth=0.2 * I3Units.radian,
            BoundsZenith=[0.0, 0.0],
            BoundsAzimuth=[0.0, 0.0],
            StepT=1.0 * I3Units.ns,
            BoundsT=time_bounds,
        )

        return steps

    # Temporarily unused but may be useful in the future.
    # def checkNames(frame: I3Frame, names: List[str]) -> None:
    #     for name in names:
    #         checkName(frame, name)

    @staticmethod
    @traysegment
    def prepare_frames(tray, name, logger, **kwargs):
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
            InputHitSeriesMapName=Splinempe.base_pulseseries,
            OutputHitSeriesMapName=Splinempe.rt_cleaned_pulseseries,
            STConfigService=seededRTConfig,
            SeedProcedure="HLCCoreHits",
            NHitsThreshold=2,
            MaxNIterations=3,
            Streams=[I3Frame.Physics],
        )

        tray.Add(checkName, name=Splinempe.rt_cleaned_pulseseries)

        # from icetray/filterscripts/python/baseproc.py
        tray.AddModule(
            "I3TimeWindowCleaning<I3RecoPulse>",
            "BaseProc_TimeWindowCleaning",
            InputResponse=Splinempe.rt_cleaned_pulseseries,
            OutputResponse=Splinempe.cleaned_muon_pulseseries,
            TimeWindow=6000 * I3Units.ns,
        )

        tray.Add(checkName, name=Splinempe.cleaned_muon_pulseseries)

    @staticmethod
    @traysegment
    def traysegment(tray, name, logger, **kwargs):
        """SplineMPE reco"""

        def checkName(frame: I3Frame, name: str) -> None:
            if name not in frame:
                raise RuntimeError(f"{name} not in frame.")
            else:
                logger.debug(f"Check that {name} is in frame: -> success.")

        # Names used in the segment.
        energy_reco_seed = "OnlineL2_BestFit"
        energy_estimator = "OnlineL2_BestFit_MuEx"

        vertex_seed = cfg.OUTPUT_PARTICLE_NAME
        # Here, "OnlineL2_SplineMPE" was used for the offline SplineMPE scan implementation.

        # Notify start.
        def notify0(frame):
            logger.debug(
                f"starting a new SplineMPE fit ({name})! {datetime.datetime.now()}"
            )

        tray.Add(notify0, "notify0")

        # Check that the base pulses are in the input frame.
        tray.Add(checkName, name=base_pulseseries)

        # =========================================================
        # ENERGY ESTIMATOR SEEDING
        # Provide SplineMPE with energy estimation from MuEx
        # This should improve the following SplineMPE track reco.
        # =========================================================

        tray.AddModule(checkName, name=energy_reco_seed)

        def notify_muex(frame):
            logger.debug(
                f"Pulse cleaning done! Now running MuEX - {datetime.datetime.now()}"
            )

        tray.Add(notify_muex, "notify_muex")

        def log_frame(frame):
            logger.debug(f"{repr(frame)}/{frame}")

        # From icetray/filterscript/python/onlinel2filter.py
        tray.AddModule(
            "muex",
            energy_estimator,
            pulses=cleaned_muon_pulseseries,
            rectrk=energy_reco_seed,
            result=energy_estimator,
            energy=True,
            detail=True,
            compat=False,
            lcspan=0,
            If=lambda f: True,
        )
        tray.Add(log_frame, "logframe")
        # ==============================================================================
        # MAIN RECONSTRUCTION
        # Default configuration takes from SplineMPE "max"
        # Multiple energy estimators can be provided but they should be run beforehand.
        # =============================================================================

        tray.AddModule(checkName, name=energy_estimator)

        bare_mu_spline, stoch_spline, noise_spline = Splinempe.get_splines()
        tray.Add(
            "I3SplineRecoLikelihoodFactory",
            "splinempe-llh",
            PhotonicsService=bare_mu_spline,
            PhotonicsServiceStochastics=stoch_spline,
            PhotonicsServiceRandomNoise=noise_spline,
            ModelStochastics=False,
            NoiseModel=Splinempe.get_noise_model(),
            Pulses=cleaned_muon_pulseseries,
            E_Estimators=[energy_estimator],
            Likelihood="MPE",
            NoiseRate=10 * I3Units.hertz,
            PreJitter=0,
            PostJitter=Splinempe.get_postjitter(),
            KSConfidenceLevel=Splinempe.get_KS_confidence_level(),
            ChargeCalcStep=0,
            CutMode="late",
            EnergyDependentJitter=Splinempe.get_energy_dependent_jitter(),
            EnergyDependentMPE=Splinempe.get_energy_dependent_MPE(),
        )

        # simplex should be the default
        # note that IMinuitMinimizer also provides a simplex algorithm
        tray.context["simplex"] = scipymin.SciPyMinimizer(
            name="scipy_simplex_f",
            method="Nelder-Mead",
            tolerance=0.1,  # this was parameterized in the original code
            max_iterations=Splinempe.get_simplex_max_iterations(),
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
        steps = Splinempe.get_steps()
        tray.Add(
            "I3SimpleParametrizationFactory",
            "splinempe-param",
            **steps,
        )

        tray.Add(checkName, name=vertex_seed)

        tray.Add(
            "I3BasicSeedServiceFactory",
            "splinempe-seed",
            FirstGuess=vertex_seed,
            # multiple can be provided as FirstGuesses=[,]
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

    @staticmethod
    def to_recopixelvariation(frame: I3Frame, geometry: I3Frame) -> RecoPixelVariation:
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
