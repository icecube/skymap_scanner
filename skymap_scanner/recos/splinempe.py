"""IceTray segment for a dummy reco."""


import datetime
import numpy as np
import os
from pathlib import Path


from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    dataclasses,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    millipede,
    photonics_service,
    recclasses,
    simclasses,
)
from icecube.icetray import I3Frame  # type: ignore[import]

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from . import RecoInterface


class SplineMPE(RecoInterface):
    """Logic for SplineMPE reco."""

    spline_path = Path(os.path.expandvars("$I3_DATA")) / "photon-tables/splines"

    BareMuTimingSpline = spline_path / "InfBareMu_mie_prob_z20a10_V2.fits"
    BareMuAmplitudeSpline = spline_path / "InfBareMu_mie_abs_z20a10_V2.fits"
    StochTimingSpline = spline_path / "InfHighEStoch_mie_prob_z20a10.fits"
    StochAmplitudeSpline = spline_path / "InfHighEStoch_mie_abs_z20a10.fits"

    def get_prejitter(self, config="max") -> int:
        return 2 if config == "max" else 4

    def get_splines(
        self,
    ) -> tuple[
        photonics_service.I3PhotoSplineService,
        photonics_service.I3PhotoSplineService,
        photonics_service.I3PhotoSplineService,
    ]:
        bare_mu_spline = photonics_service.I3PhotoSplineService(
            self.BareMuAmplitudeSpline,
            self.BareMuTimingSpline,
            timingSigma=self.get_prejitter(),
        )
        stoch_spline = photonics_service.I3PhotoSplineService(
            self.StochAmplitudeSpline,
            self.StochTimingSpline,
            timingSigma=self.get_prejitter(),
        )
        noise_spline = photonics_service.I3PhotoSplineService(
            self.BareMuAmplitudeSpline, self.BareMuTimingSpline, timingSigma=1000
        )
        return bare_mu_spline, stoch_spline, noise_spline

    def get_noise_model(self, config="max"):
        return "SRT" if config == "max" else "none"

    def get_energy_estimators(self):
        return ["OnlineL2_BestFit_MuEx"]

    def get_pulses_name(self):
        # for reference, Millipede uses:
        ## pulsesName_orig = "SplitUncleanedInIcePulses"
        ## pulsesName = "SplitUncleanedInIcePulsesIC"
        ## pulsesName_cleaned = pulsesName+'LatePulseCleaned'
        return "OnlineL2_CleanedMuonPulses"

    def get_postjitter(self, config="max"):
        return 2 if config == "max" else 0

    def get_KS_confidence_level(self, do_KS=False):
        return 5 if do_KS else 0

    def get_energy_dependent_jitter(self, config="max"):
        return True if config == "max" else False

    def get_energy_dependent_MPE(self, config="max"):
        return True if config == "max" else False

    def get_steps(self):
        vertex_step = 20 * I3Units.m
        vertex_bound = 2000 * I3Units.m
        vertex_bounds = [-vertex_bound, +vertex_bound]

        steps = dict(
            StepX=vertex_step,
            StepY=vertex_step,
            StepZ=vertex_step,
            BoundsX=vertex_bounds,
            BoundsY=vertex_bounds,
            BoundsZ=vertex_bounds,
            StepZenith=0.1 * I3Units.radian,
            StepAzimuth=0.2 * I3Units.radian,
            BoundsZenith=None,
            BoundsAzimuth=None,
            StepT=1.0 * I3Units.ns,
            BoundsT=500 * I3Units.ns,
        )

        return steps

    @staticmethod
    @icetray.traysegment
    def traysegment(tray, name, logger, **kwargs):
        """SplineMPE reco"""

        def notify0(frame):
            logger.debug(
                f"starting a new SplineMPE fit ({name})! {datetime.datetime.now()}"
            )

        tray.Add(notify0, "notify0")

        bare_mu_spline, stoch_spline, noise_spline = self.get_splines()

        tray.Add(
            "I3SplineRecoLikelihoodFactory",
            "splinempe-llh",
            PhotonicsService=bare_mu_spline,
            PhotonicsServiceStochastics=stoch_spline,
            PhotonicsServiceRandomNoise=noise_spline,
            ModelStochastics=False,
            NoiseModel=self.get_noise_model(),
            Pulses=self.get_pulses_name(),
            E_Estimators=self.get_energy_estimators(),
            Likelihood="MPE",
            NoiseRate=10 * I3Units.hertz,
            PreJitter=0,
            PostJitter=self.get_postjitter(),
            KSConfidenceLevel=self.get_KS_confidence_level(),
            ChargeCalcStep=0,
            CutMode="late",
            EnergyDependentJitter=self.get_energy_dependent_jitter(),
            EnergyDependentMPE=self.get_energy_dependent_MPE(),
        )

        # simplex should be the default
        # note that IMinuitMinimizer also provides a simplex algorithm
        tray.context["simplex"] = lilliput.scipymin.SciPyMinimizer(
            name="scipy_simplex_f",
            method="Nelder-Mead",
            tolerance=0.1,  # this was parameterized in the original code
            max_iterations=max_iter,
        )

        # iminuit can be disabled if not necessary
        tray.context["iminuit"] = lilliput.i3minuit.IMinuitMinimizer(
            name="iminuit",
            Tolerance=10,
            MaxIterations=1000,
            MinuitStrategy=2,
            MinuitPrintLevel=0,
        )

        steps = self.get_steps()

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
            pixel=frame[cfg.I3FRAME_PIXEL].value,
            llh=frame["splinempe-reco"].value,
            reco_losses_inside=np.NaN,
            reco_losses_total=np.NaN,
            pos_var_index=frame[cfg.I3FRAME_POSVAR].value,
            position=frame["splinempe-reco"].pos,
            time=frame["splinempe-reco"].time,
            energy=frame["splinempe-reco"].energy,
        )
