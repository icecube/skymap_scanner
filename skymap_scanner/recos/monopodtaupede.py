"""IceTray segment for a millipede reco."""

# fmt: off
# pylint: skip-file
# mypy: ignore-errors



from reco.seed import convert_seeds


import datetime
import os
from typing import Final, List, Tuple

import numpy
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
    mue,
)

from skymap_scanner import config as cfg
from skymap_scanner.utils.pixel_classes import RecoPixelVariation
from skymap_scanner.recos import RecoInterface, VertexGenerator
from skymap_scanner.recos.common.pulse_proc import mask_deepcore, pulse_cleaning


import numpy as np

from icecube.icetray import I3Units, I3Frame, logging
from icecube.millipede import HighEnergyExclusions

from reco.mlpd import preferred
from reco.seed import convert_to_tau_seed, kmeans
from functools import partial
from icecube.millipede import (
    MonopodFit,
    TaupedeFit,
)

from icecube.phys_services import I3ScaleCalculator

class MonopodTaupede(RecoInterface):
    """Reco logic for monopod+taupede."""

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
        tray.AddSegment(HighEnergyExclusions, 'millipede_DOM_exclusions',
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
    def MonopodWrapper(self,tray, name, Seed, Iterations=4, Chain=1, **params):
        # the amplitude monopod fit
        tray.Add(
            MonopodFit,
            f'seed_MonopodFit_{name}_Amp',
            Seed=Seed,
            Iterations=Iterations,
            PhotonsPerBin=-1,
            StepD=60,
            StepT=100,
            StepZenith=0,
            StepAzimuth=0,
            **{k: v for k, v in params.items() if k not in ['PhotonsPerBin', 'BinSigma']},
            )   
            Seed = [
                f'seed_MonopodFit_{name}_Amp',
            ]

        # the multiple iteration timed monopod fit
        tray.Add(
            MonopodFit,
            f'MonopodFit_{name}',
            Seed=Seed,
            Iterations=Iterations,
            StepD=20,
            StepT=50,
            StepZenith=0,
            StepAzimuth=0,
            **params,
        )

        return f'MonopodFit_{name}'
    
    @icetray.traysegment
    def TaupedeWrapper(self, tray, name, Seed, Iterations=1, Chain=1, **params):
    
        def length_penalty(_p):
            return max(0., np.log10(abs(_p.length) / I3Units.m))

        monopod0 = f'MonopodFit_{name}'
        tray.Add(self.MonopodWrapper, name, Seed=Seed, Chain=Chain, **params)

        _tparams = {
            k: v
            for k, v in params.items()
            if k
            not in [
                'Minimizer',
            ]
        }

        _nclusters = 2
        tray.Add(
            kmeans,
            nclusters=_nclusters,
            minit='++',
            pulse_type=params['Pulses'],
            output_particles_key='KMeansParticles_pp',
            split=True,
            If=lambda _fr: not _fr.Has('KMeansParticles_pp'),
        )
        tray.Add(
            kmeans,
            nclusters=_nclusters,
            minit='points',
            pulse_type=params['Pulses'],
            output_particles_key='KMeansParticles_points',
            split=True,
            If=lambda _fr: not _fr.Has('KMeansParticles_points'),
        )

        seedscans_monopod = []
        seedscans_kmeans2 = []
        seedscans_altnfit = []
        for minit in ['pp', 'points']:
            for i in range(_nclusters):
                # a fast time fit with the output of kmeans(nclusters=2)
                kmeans_tfit = f'KMeansParticles_{name}_{minit}{i:03}_T'
                tray.Add(
                    TaupedeFit,
                    kmeans_tfit,
                    Seed=f'KMeansParticles_{minit}{i:03}',
                    StepL=0.,
                    StepT=60.,
                    StepD=0.,
                    StepZenith=0.,
                    StepAzimuth=0.,
                    LengthBounds=[0., 1000.],
                    **params,
                )
                # scan vertex along direction
                for dist in range(-100, 101, 20):
                    kmeans_seed_key = f'seed_{kmeans_tfit}{dist:04}'
                    tray.Add(
                        convert_to_tau_seed,
                        inkey=kmeans_tfit,
                        outkey=kmeans_seed_key,
                        length=None, backprop=dist * I3Units.m
                    )
                    seedscans_kmeans2.append(kmeans_seed_key)

        def contained_p2(frame, seed_key):
            if frame.Stop != I3Frame.Physics:
                return False

            if not frame.Has(seed_key):
                return False

            # guarantee seed for short lengths
            if frame[seed_key].length < 30 * I3Units.m:
                return True

            p2 = frame[seed_key].pos + frame[seed_key].dir * frame[seed_key].length
            # this places the second cascade at the monopod vtx, which we trust
            # treat the start as the secondary vertex
            if '_Backlen' in seed_key:
                p2 = frame[seed_key].pos

            # skip if secondary vertex is outside
            if abs(p2.z) > 530. * I3Units.m:
                return False

            if p2.x**2 + p2.y**2 > (600. * I3Units.m)**2:
                return False

            return True
            for len in np.unique(np.logspace(0, 2.8, 50, dtype=int)):
                monopod_seed_key = f'seed_{name}_Monopod{len:03}'
                tray.Add(convert_to_tau_seed,
                        inkey=monopod0,
                        outkey=monopod_seed_key,
                        length=len * I3Units.m)
                seedscans_monopod.append(monopod_seed_key)

                backprp_seed_key = f'seed_{name}_Backprp{len:03}'
                tray.Add(
                    convert_to_tau_seed,
                    inkey=monopod0,
                    outkey=backprp_seed_key,
                    length=len * I3Units.m,
                    backprop=2. * I3Units.m
                )
                seedscans_monopod.append(backprp_seed_key)

                if len > 2. * I3Units.m:
                    backprp_seed_key = f'seed_{name}_Backlen{len:03}'
                    tray.Add(
                        convert_to_tau_seed,
                        inkey=monopod0,
                        outkey=backprp_seed_key,
                        length=len * I3Units.m,
                        backprop=len * I3Units.m,
                    )
                    seedscans_monopod.append(backprp_seed_key)

                for altdir in ['SPEFit2', 'LineFit']:
                    altdir_seed_key = f'seed_{name}_{altdir}{len:03}'
                    tray.Add(
                        convert_to_tau_seed,
                        inkey=monopod0,
                        outkey=altdir_seed_key,
                        length=len * I3Units.m,
                        dirkey=altdir,
                        If=lambda _fr, _altdir=altdir: _fr.Has(_altdir),
                    )
                    seedscans_altnfit.append(altdir_seed_key)

        for seed in seedscans_monopod + seedscans_altnfit + seedscans_kmeans2:
            tray.Add('TauMillipede', Tau=seed, Output=f'{seed}_Tau', **_tparams,
                     If=partial(contained_p2, seed_key=seed))

        tray.Add(
            preferred,
            i3_particles_fitparams=[(_, f'{_}_TauFitParams') for _ in seedscans_monopod],
            output=f'seed_{name}_BestMonopod',
            penalty=length_penalty
        )
        tray.Add(
            preferred,
            i3_particles_fitparams=[(_, f'{_}_TauFitParams') for _ in seedscans_kmeans2],
            output=f'seed_{name}_BestKMeans2',
            penalty=length_penalty
        )
        tray.Add(
            preferred,
            i3_particles_fitparams=[(_, f'{_}_TauFitParams') for _ in seedscans_altnfit],
            output=f'seed_{name}_BestAltnFit',
            penalty=length_penalty
        )
        Seed = [f'seed_{name}_BestMonopod', f'seed_{name}_BestAltnFit', f'seed_{name}_BestKMeans2']

        if isinstance(Seed, str):
            Seed = [Seed,]

        taupede_fits = []
        _outkey = ''
        for _seed in Seed:
            _outkey = f'{_seed}_TaupedeFit_{name}'
            tray.Add(
                TaupedeFit,
                _outkey,
                Seed=_seed,
                StepL=20,
                StepT=20,
                StepD=20,
                StepZenith=0,
                StepAzimuth=0,
                LengthBounds=[0, 1000],
                Iterations=Iterations,
                **params,
            )
            taupede_fits.append(_outkey)

        tray.Add(
            preferred,
            i3_particles_fitparams=[(_, f'{_}FitParams') for _ in taupede_fits],
            output=f'TaupedeFit_{name}',
            penalty=length_penalty
        )
        def copy_params_particles(frame):
            print(name)
            pref_key = frame[f'TaupedeFit_{name}_key'].value

            if frame.Has(f'{pref_key}FitParams'):
                frame[f'TaupedeFit_{name}FitParams'] = frame[f'{pref_key}FitParams']
            else:
                logging.log_warn(
                    f'Frame does not contain "{pref_key}FitParams", check if I3SimpleFitter was successful'
                )

            if frame.Has(f'{pref_key}Particles'):
                frame[f'TaupedeFit_{name}Particles'] = frame[f'{pref_key}Particles']
            else:
                logging.log_warn(
                    f'Frame does not contain "{pref_key}Particles", check if I3SimpleFitter was successful'
                )

        tray.Add(copy_params_particles)

        return _outkey


    @icetray.traysegment
    def traysegment(self, tray, name, logger, seed=None):
        """Perform MonopodTaupede reco."""
        #take out prep frames after testing
        #tray.AddSegment(self.prepare_frames,"prepareframes",logger=logger)
        ExcludedDOMs = tray.Add(self.exclusions)

        tray.Add(self.makeSurePulsesExist, pulsesName=self.pulsesName_cleaned)

        def check_cal(frame):
            cal = frame['I3Calibration']
            logger.debug('Mean SPEs')
            for omkey in list(cal.dom_cal.keys())[::100]:
                x = cal.dom_cal[omkey]
                mean_spe = dataclasses.mean_spe_charge(x)
                logger.debug(f'...{omkey}: {mean_spe} {x.mean_atwd_charge_correction}')
                logger.debug(f'......: {x.combined_spe_charge_distribution.compensation_factor}')
        tray.Add(check_cal)

        def notify0(frame):
            logger.debug(f"starting a new fit ({name})! {datetime.datetime.now()}")
        tray.AddModule(notify0, "notify0")


        seed= tray.AddSegment(convert_seeds, name, hypo='cascade', seeds=seed)

        reco_params = {
            'Pulses': self.pulsesName_cleaned,
            'CascadePhotonicsService': self.cascade_service,
            'MuonPhotonicsService': self.muon_service,
            'ExcludedDOMs': ExcludedDOMs,
            'PartialExclusion': True,
            'ShowerRegularization': 1.e-12,
            'MinTimeWidth':12,
            'BinSigma': np.nan,
            'RelUncertainty':0.05,
            'ReadoutWindow':self.pulsesName_cleaned + 'TimeRange',
            'Minimizer':'iMIGRAD',
            'UseUnhitDOMS': True,
            'PhotonsPerBin':0,
        }



        tray.Add(self.TaupedeWrapper,
                'Final',
                Seed=seed,
                Iterations=1,
                Chain=1,
                **reco_params)

                                              
    
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

        if 'TaupedeFit_FinalFitParams' not in frame:
            llh = float("nan")
        else:
            llh = frame['TaupedeFit_FinalFitParams'].logl
        return RecoPixelVariation(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel_id=frame[cfg.I3FRAME_PIXEL].value,
            llh=llh,
            reco_losses_inside=reco_losses_inside,
            reco_losses_total=reco_losses_total,
            posvar_id=frame[cfg.I3FRAME_POSVAR].value,
            position=frame['TaupedeFit_FinalParticles'][0].pos,
            time=frame['TaupedeFit_FinalParticles'][0].time,
            energy=frame['TaupedeFit_FinalParticles'][0].energy,
        )

    @staticmethod
    def get_reco_losses_inside(p_frame: I3Frame, g_frame: I3Frame) -> Tuple[float, float]:

        if 'TaupedeFit_FinalParticles' not in p_frame:
            return numpy.nan, numpy.nan
        recoParticle = p_frame['TaupedeFit_FinalParticles']

        calc = I3ScaleCalculator(g_frame["I3Geometry"], I3ScaleCalculator.IC86_STRICT, I3ScaleCalculator.IT81_STRICT)

        """
        def getRecoLosses(vecParticles):
            losses = []
            for p in vecParticles:
                if not p.is_cascade:
                    continue
                if p.energy == 0.:
                    continue
                losses.append([p.time, p.energy])
            return losses
        recoLosses = getRecoLosses(p_frame['TaupedeFit_FinalParticles'])

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
        """

        totalRecoLosses = 0.
        totalRecoLossesInside = 0.
        for particle in recoParticle:
            totalRecoLosses += particle.energy
            contained = calc.vertex_is_inside(particle)
            if contained:
                totalRecoLossesInside += particle.energy

        return totalRecoLossesInside, totalRecoLosses

RECO_CLASS: Final[type[RecoInterface]] = MonopodTaupede
