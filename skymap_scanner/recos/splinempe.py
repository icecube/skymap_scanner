"""IceTray segment for a dummy reco."""


import datetime
import numpy as np
import os
from pathlib import Path


from I3Tray import I3Units  # type: ignore[import]

# icecube module imports are required to make IceTray modules and services available.
from icecube import (  # type: ignore[import]  # noqa: F401
    dataclasses,
    DomTools,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    lilliput,
    spline_reco,
    photonics_service,
    recclasses,
    simclasses,
    STTools
)

# Class bindings directly accessed by the python code are imported explicitly.
from icecube.icetray import I3Frame, traysegment  # type: ignore[import]
from icecube.lilliput import scipymin, i3minuit  # type: ignore[import]
from icecube.phys_services.which_split import which_split  # type: ignore[import]
from icecube.photonics_service import I3PhotoSplineService  # type: ignore[import]
from icecube.STTools.seededRT.configuration_services import I3DOMLinkSeededRTConfigurationService  # type: ignore[import]

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from . import RecoInterface


class Splinempe(RecoInterface):
    """Logic for SplineMPE reco."""

    spline_path = Path(os.path.expandvars("$I3_DATA")) / "photon-tables/splines"

    BareMuTimingSpline = str(spline_path / "InfBareMu_mie_prob_z20a10_V2.fits")
    BareMuAmplitudeSpline = str(spline_path / "InfBareMu_mie_abs_z20a10_V2.fits")
    StochTimingSpline = str(spline_path / "InfHighEStoch_mie_prob_z20a10.fits")
    StochAmplitudeSpline = str(spline_path / "InfHighEStoch_mie_abs_z20a10.fits")

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
    def get_energy_estimators():
        return ["OnlineL2_BestFit_MuEx"]

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

    @staticmethod
    def checkPulsesName(frame, pulsesName) -> None:
        if pulsesName not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName + "TimeWindows" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName + "TimeWindows"))
        if pulsesName + "TimeRange" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName + "TimeRange"))
    
    @staticmethod
    def checkNames(frame, names) -> None:
        for name in names:
            if name not in frame:
                raise RuntimeError(f"{name} not in frame")

    @staticmethod
    @traysegment
    def traysegment(tray, name, logger, **kwargs):
        """SplineMPE reco"""

        def notify0(frame):
            logger.debug(
                f"starting a new SplineMPE fit ({name})! {datetime.datetime.now()}"
            )

        tray.Add(notify0, "notify0")

        base_pulseseries = "SplitUncleanedInIcePulses"

        tray.Add(Splinempe.checkPulsesName, pulsesName = base_pulseseries)
        tray.Add(Splinempe.checkNames, names = Splinempe.get_energy_estimators())

        # PULSE CLEANING: from "SplitUncleanedInIcePulses" to "OnlineL2_CleanedMuonPulses".

        # from icetray/filterscripts/python/all_filters.py
        # RT = Radius and Time
        seededRTConfig = I3DOMLinkSeededRTConfigurationService(
            ic_ic_RTRadius=150.0 * I3Units.m,
            ic_ic_RTTime=1000.0 * I3Units.ns,
            treat_string_36_as_deepcore=False,
            useDustlayerCorrection=False,
            allowSelfCoincidence=True,
        )

        # from icetray/filterscripts/python/baseproc.py
        rt_cleaned_pulseseries = "SplitRTCleanedInIcePulses"
        tray.AddModule(
            "I3SeededRTCleaning_RecoPulseMask_Module",
            "BaseProc_RTCleaning",
            InputHitSeriesMapName=base_pulseseries,
            OutputHitSeriesMapName=rt_cleaned_pulseseries,
            STConfigService=seededRTConfig,
            SeedProcedure="HLCCoreHits",
            NHitsThreshold=2,
            MaxNIterations=3,
            Streams=[I3Frame.Physics],
            If=which_split(split_name="InIceSplit"),
        )

        # from icetray/filterscripts/python/baseproc.py
        cleaned_muon_pulseseries = "CleanedMuonPulses"
        tray.AddModule(
            "I3TimeWindowCleaning<I3RecoPulse>",
            "BaseProc_TimeWindowCleaning",
            InputResponse=rt_cleaned_pulseseries,
            OutputResponse=cleaned_muon_pulseseries,
            TimeWindow=6000 * I3Units.ns,
            If=which_split(split_name="InIceSplit"),
        )

        tray.Add(Splinempe.checkPulsesName, pulsesName = cleaned_muon_pulseseries)

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
            E_Estimators=Splinempe.get_energy_estimators(),
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

        # iminuit can be disabled if not necessary
        tray.context["iminuit"] = i3minuit.IMinuitMinimizer(
            name="iminuit",
            Tolerance=10,
            MaxIterations=1000,
            MinuitStrategy=2,
            MinuitPrintLevel=0,
        )

        steps = Splinempe.get_steps()

        tray.Add(
            "I3SimpleParametrizationFactory",
            "splinempe-param",
            **steps,
        )

        # the original splineMPE scan used OnlineL2_SplineMPE as a seed
        tray.Add(
            "I3BasicSeedServiceFactory",
            "splinempe-seed",
            FirstGuess=cfg.OUTPUT_PARTICLE_NAME,
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

        def notify1(frame):
            logger.debug(f"SplineMPE pass done! {datetime.datetime.now()}")

        tray.Add(notify1, "notify1")

    @staticmethod
    def to_recopixelvariation(frame: I3Frame, geometry: I3Frame) -> RecoPixelVariation:
        return RecoPixelVariation(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel_id=frame[cfg.I3FRAME_PIXEL].value,
            llh=frame["splinempe-reco" + "FitParams"].logl,  # FitParams is hardcoded
            reco_losses_inside=np.NaN,
            reco_losses_total=np.NaN,
            posvar_id=frame[cfg.I3FRAME_POSVAR].value,
            position=frame["splinempe-reco"].pos,
            time=frame["splinempe-reco"].time,
            energy=frame["splinempe-reco"].energy,
        )
