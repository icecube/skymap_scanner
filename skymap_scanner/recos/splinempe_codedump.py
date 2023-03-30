"""IceTray segment for a splinempe reco."""

from . import RecoInterface

from icecube import dataio, dataclasses, gulliver, lilliput, icetray, spline_reco
from icecube.lilliput import scipymin, i3minuit
from icecube.photonics_service import I3PhotoSplineService
from icecube.icetray import I3Units
import os
from pathlib import Path


class GulliverFitter:
    """Wrapper around a Gulliver object

    Attributes:
            para_m -> general parametrization
            vert_step -> step used in the minimization process for the vertex
            vert_max -> maximum range in the minimization process for the vertex
            param_set_dictionary -> dictionary for the parameters
            params -> names of the parameters in which the minimizator operates
            mini -> minimizer used by the gulliver object
            fitter -> the effective gulliver object

    Behaviours:
            evaluate_hypo() -> Evaluates an hypotesis (I3Particle) with a SplineMPE fit
    """

    def __init__(
        self,
        params,  # String that defines which are the parameters to use
        # for the minimization. The possible entries are:
        # - 'all' All the parameters (vertex+direction)
        #         are minimized at the same time.
        #         if time == True it is
        #         vertex+direction+time.
        # - 'vertex' The vertex is minimized while the
        #            direction remains fixed.
        # - 'time' Only the time is minimized
        llh,  # The llh object at which the gulliver object
        # is associated.
        vertmax=2000.0,  # Maximum distance in meters at which the vertex can
        # be translated in a direction during a minimization
        # of the likelihood.
        max_iter=100,  # Maximum number of iterations of the minimization
        # algorithm.
        tol=0.1,  # Parameter to control when the minimization process
        # stops.
        vertstep=20.0,  # Steps in meters for the minimization on the vertex.
        time=False,  # Boolean value, if true also the time is taken into
        # account as a parameter to minimize on.
        timestep=1.0,  # Steps in nanoseconds for the minimization on the time.
        timemax=500.0,  # Maximum time in nanosecond at which the time can be
        # translated during a minimization of the likelihood.
        minimizer="simplex",  # Minimizer to use: or simplex, or minuit.
        azstep=0.2,  # steps for the azimuth minimization
        zenstep=0.1,  # steps for the zenith minimization
        azbound=None,
        zenbound=None,
    ):
        self.para_m = lilliput.I3SimpleParametrization("simple_para_medium")

        ang_u = I3Units.radian
        self.vert_step = vertstep * I3Units.m
        self.vert_max = vertmax * I3Units.m

        if time:
            param_keys = ["zen", "az", "x", "y", "z", "t"]

            param_dict = {
                "zen": lilliput.I3SimpleParametrization.PAR_Zen,
                "az": lilliput.I3SimpleParametrization.PAR_Azi,
                "x": lilliput.I3SimpleParametrization.PAR_X,
                "y": lilliput.I3SimpleParametrization.PAR_Y,
                "z": lilliput.I3SimpleParametrization.PAR_Z,
                "t": lilliput.I3SimpleParametrization.PAR_T,
            }

            self.time_step = timestep * I3Units.ns
            self.time_max = timemax * I3Units.ns

            self.param_set_dict = {
                "zen": {"step": zenstep * ang_u, "bound": zenbound},
                "az": {"step": azstep * ang_u, "bound": azbound},
                "x": {"step": self.vert_step, "bound": self.vert_max},
                "y": {"step": self.vert_step, "bound": self.vert_max},
                "z": {"step": self.vert_step, "bound": self.vert_max},
                "t": {"step": self.time_step, "bound": self.time_max},
            }

            if not isinstance(params, list):
                if params == "all":
                    self.params = param_keys
                elif params == "vertex":
                    self.params = ["x", "y", "z"]
                elif params == "time":
                    self.params = ["t"]

        else:
            # not fitting time
            param_keys = ["zen", "az", "x", "y", "z"]

            param_dict = {
                "zen": lilliput.I3SimpleParametrization.PAR_Zen,
                "az": lilliput.I3SimpleParametrization.PAR_Azi,
                "x": lilliput.I3SimpleParametrization.PAR_X,
                "y": lilliput.I3SimpleParametrization.PAR_Y,
                "z": lilliput.I3SimpleParametrization.PAR_Z,
            }

            self.param_set_dict = {
                "zen": {"step": zenstep * ang_u, "bound": zenbound},
                "az": {"step": azstep * ang_u, "bound": azbound},
                "x": {"step": self.vert_step, "bound": self.vert_max},
                "y": {"step": self.vert_step, "bound": self.vert_max},
                "z": {"step": self.vert_step, "bound": self.vert_max},
            }

            if not isinstance(params, list):
                if params == "all":
                    self.params = param_keys
                elif params == "vertex":
                    self.params = ["x", "y", "z"]

        for par in self.params:
            param = param_dict[par]
            param_set = self.param_set_dict[par]
            self.para_m.SetStep(param, param_set["step"], True)
            if param_set["bound"] is not None:
                self.para_m.SetAbsBounds(
                    param, -param_set["bound"], param_set["bound"], True
                )

        mini = self.build_minimizer(minimizer)

        self.fitter = gulliver.I3Gulliver("fitter_m", llh, self.para_m, mini)

    def build_minimizer(self, minimizer):
        if minimizer == "simplex":
            mini = scipymin.SciPyMinimizer(
                name="scipy_simplex_f",
                method="Nelder-Mead",
                tolerance=tol,
                max_iterations=max_iter,
            )
        elif minimizer == "iminuit":
            mini = i3minuit.IMinuitMinimizer(
                name="iminuit",
                Tolerance=10,
                MaxIterations=1000,
                MinuitStrategy=2,
                MinuitPrintLevel=0,
            )
        else:
            raise NotImplementedError(f"Minimizer {minimizer} is not known.")

        return mini

    def fit(self, particle):
        """[Given an hypothesis (I3Particle), it returns the results of a SplineMPE fit made
            using it as a seed]

        Args:
            particle ([I3Particle]): The hypothesis to evaluate.

        Returns:
            params.logl ([float]): value of the log likelihood of the best fit.
            hypo ([I3GulliverHypothesis]): the result of the best fit, cont.particle is the
                                           best fitting particle.
        """
        hypo = gulliver.I3EventHypothesis(particle)
        params = self.fitter.Fit(hypo)

        return params.logl, hypo


class SplineMPE(RecoInterface):
    spline_path = Path(os.path.expandvars("$I3_DATA")) / "photon-tables/splines"

    BareMuTimingSpline = spline_path / "InfBareMu_mie_prob_z20a10_V2.fits"
    BareMuAmplitudeSpline = spline_path / "InfBareMu_mie_abs_z20a10_V2.fits"
    StochTimingSpline = spline_path / "InfHighEStoch_mie_prob_z20a10.fits"
    StochAmplitudeSpline = spline_path / "InfHighEStoch_mie_abs_z20a10.fits"
    # EffectiveDistanceSpline = (
    #    spline_path / "cascade_effectivedistance_spice_bfr-v2_z20.eff.fits"
    # )

    def init_splines(self) -> None:
        self.bare_mu_spline = I3PhotoSplineService(
            self.BareMuAmplitudeSpline,
            self.BareMuTimingSpline,
            timingSigma=self.PreJitter,
        )
        self.stoch_spline = I3PhotoSplineService(
            self.StochAmplitudeSpline,
            self.StochTimingSpline,
            timingSigma=self.PreJitter,
        )
        self.noise_spline = I3PhotoSplineService(
            self.BareMuAmplitudeSpline, self.BareMuTimingSpline, timingSigma=1000
        )

    def build_llh(self) -> spline_reco.I3SplineRecoLikelihood:
        llh = spline_reco.I3SplineRecoLikelihood()
        llh.PhotonicsService = self.bare_mu_spline
        llh.PhotonicsServiceStochastics = self.stoch_spline
        llh.PhotonicsServiceRandomNoise = self.noise_spline
        llh.ModelStochastics = False
        llh.NoiseModel = self.NoiseModel
        llh.Pulses = self.PulsesName
        llh.E_Estimators = self.EnergyEstimators
        llh.Likelihood = "MPE"
        llh.NoiseRate = 10 * I3Units.hertz
        llh.PreJitter = 0
        llh.PostJitter = self.PostJitter
        llh.KSConfidenceLevel = self.KSConfidenceLevel
        llh.ChargeCalcStep = 0
        llh.CutMode = "late"
        llh = self.EnergyDependentJitter
        llh = self.EnergyDependentMPE
        return llh

    def init_config(self, configuration, KS):
        # defaults
        self.NoiseModel = "none"
        self.PreJitter = 4
        self.PostJitter = 0
        self.KSConfidenceLevel = 0
        self.EnergyDependentJitter = False
        self.EnergyDependentMPE = False
        # enable modifications depending on configuration
        if configuration != "default":
            self.KSConfidenceLevel = 5
            self.EnergyDependentMPE = True
        if configuration == "recommended" or configuration == "max":
            self.PreJitter = 2
            self.PostJitter = 2
            self.EnergyDependentJitter = True
        if configuration == "max":
            self.NoiseModel = "SRT"
        if not KS:
            self.KSConfidenceLevel = 0

    def __init__(self, configuration="default", KS=True):
        # sets configuration variables as attributes
        self.init_config(configuration=configuration, KS=KS)

        # builds and sets splines as attributes
        self.init_splines()  # uses self.PreJitter

        llh = self.build_llh()

        # Important: vertex_fitter modifies llh!
        self.vertex_fitter = GulliverFitter("vertex", llh)

    def scan_direction(self, frame, zenith, azimuth, time_minimization=False, time_fitter = None):
        # This is supposed to get the seed for the KS test.
        seed_particle = frame[seed_name]
        _prefit_result, _prefit_hypo = self.vertex_fitter.fit(seed_particle)

        direction = dataclasses.I3Direction(zenith, azimuth)

        # If the mode is 'default', 7 seed vertices are produced for each direction.
        if mode == "default":
            pos_seeds = self.get_vertex_seeds(
                seed_cp.pos, direc, r_ax=r_ax, v_ax=v_ax, ang_steps=3
            )
            vals, particles = [], []

            # A gulliver fit is performed for each vertex.
            for j in range(len(pos_seeds)):
                particle = self.pos_dir2part(seed_cp, pos_seeds[j], direc)
                fitparams, hypo = self.vertex_fitter.fit(particle)
                vals.append(fitparams.logl)
                particles.append(copy.copy(hypo.particle))

            min_ind = np.nanargmin(vals)
            logl = vals[min_ind]
            coords = [
                particles[min_ind].pos.x,
                particles[min_ind].pos.y,
                particles[min_ind].pos.z,
            ]

            # Minimization on the time, if required.
            if time_minimization:
                seed = particles[min_ind]
                fitparams, hypo = time_fitter.fit(seed) 
                logl = fitparams.logl

        elif mode == "fast":
            # only the seed vertex is used for each direction.
            particle = self.pos_dir2part(seed_cp, seed_cp.pos, direc)
            fitparams, hypo = self.vertex_fitter.fit(particle)
            logl = fitparams.logl
            coords = seed_cp.pos

        return logl, coords

    def get_vertex_seeds(
        self, vert_mid, direc, v_ax=[-40.0, 40.0], r_ax=[150.0], ang_steps=3
    ):
        """[Given a vertex and a direction it returns some vertex seeds to perform a SplineMPE fit
            these vertexes are by default 7, one is the initial one, the othes 6 are chosen along
            a cylinder with characteristics specified by v_ax and r_ax and ang_steps]

        Args:
            vert_mid ([I3Position]): The initial vertex
            direc ([]): The direction in the sky
            v_ax ([list of floats], optional): the list of steps along the direction to do to find
                                               the vertexes
            r_ax ([list of floats], optional): the list of radius of the cylinders used to find the
                                               vertexes
            ang_steps([int], optional): the number of seeds to be taken on each basis of a cylinder

        Returns:
            pos_seeds ([list of I3Position]): the list of vertex seeds
        """

        vert_u = I3Units.m

        if isinstance(direc, tuple):
            theta, phi = direc
        else:
            theta = direc.theta
            phi = direc.phi

        ang_ax = np.linspace(0, 2.0 * np.pi, ang_steps + 1)[:-1]

        # Angular space batween each seed.
        dang = (ang_ax[1] - ang_ax[0]) / 2.0

        v_dir, dir1, dir2 = self.get_prop_perp_direcs(theta, phi)

        # In the following, the function constructs a list of seed vertexes.
        pos_seeds = [vert_mid]

        for i, vi in enumerate(v_ax):
            v = vi * v_dir

            for j, r in enumerate(r_ax):
                for ang in ang_ax:
                    d1 = r * np.cos(ang + (i + j) * dang) * dir1
                    d2 = r * np.sin(ang + (i + j) * dang) * dir2

                    x = v[0] + d1[0] + d2[0]
                    y = v[1] + d1[1] + d2[1]
                    z = v[2] + d1[2] + d2[2]

                    pos = dataclasses.I3Position(
                        vert_mid.x + x * vert_u,
                        vert_mid.y + y * vert_u,
                        vert_mid.z + z * vert_u,
                    )

                    pos_seeds.append(pos)

        return pos_seeds

    # @staticmethod
    # def to_pixelreco(frame: I3Frame, geometry: I3Frame) -> "PixelReco":
    #    return super().to_pixelreco(frame, geometry)
