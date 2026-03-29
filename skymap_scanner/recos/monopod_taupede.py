import datetime
import os
from typing import Final, List 

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
    simclasses
)


from icecube.icetray import I3Frame, I3Units, I3Tray

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from . import RecoInterface, VertexGenerator
from .common.pulse_proc import mask_deepcore, pulse_cleaning



import random


#IMPORTS FROM REC_TAU:
import argparse
from importlib.metadata import version

from pprint import pformat
import numpy as np

from icecube import dataio
from icecube.phys_services.which_split import which_split
from icecube.millipede import HighEnergyExclusions
from icecube.spline_reco import SplineMPE
from icecube.level3_filter_cascade.level3_Recos import SPEFit

# for level 3 muon (pulse cleaning needed for splinempe)
from icecube import level3_filter_muon  # noqa: F401

# for srt cleaning
from icecube.STTools.seededRT.configuration_services import I3DOMLinkSeededRTConfigurationService

# for gulliver
from icecube.gulliver_modules import gulliview

from snowflake import library, unfold
import reco
from reco import skymap, dom
from reco.masks import (earlypulses,
                        maskdc,
                        maskunhits,
                        maskstrings,
                        maskdust,
                        pulse_cleaning)
from reco.truth import truth, druth
from reco.mlpd import (MonopodWrapper,
                       TaupedeWrapper,
                       MillipedeWrapper,
                       preferred,
                       define_splines)
from reco.seed import default_seeds

class MonoTau(RecoInterface):

    #SPLINE SETTINGS TAKEN FROM MILLIPEDE_WILKS:

    FTP_ABS_SPLINE = "cascade_single_spice_ftp-v1_flat_z20_a5.abs.fits"
    FTP_PROB_SPLINE = "cascade_single_spice_ftp-v1_flat_z20_a5.prob.v2.fits"
    FTP_EFFD_SPLINE = "cascade_effectivedistance_spice_ftp-v1_z20.eff.fits"
    FTP_EFFP_SPLINE = "cascade_effectivedistance_spice_ftp-v1_z20.prob.fits"
    FTP_TMOD_SPLINE = "cascade_effectivedistance_spice_ftp-v1_z20.tmod.fits"

    SPLINE_REQUIREMENTS = [FTP_ABS_SPLINE, FTP_PROB_SPLINE, FTP_EFFD_SPLINE,
                           FTP_EFFP_SPLINE, FTP_TMOD_SPLINE]

    """Logic for a dummy reco."""

    def __init__(self, realtime_format_version: str):
        super().__init__(realtime_format_version)
        self.rotate_vertex = True
        self.refine_time = True
        #VALUE TAKEN FROM MILLIPEDE_WILKS:
        self.add_fallback_position = True

  
    def get_vertex_variations() -> List[dataclasses.I3Position]:
        """Returns a list of vectors referenced to the origin that will be used to generate the vertex position variation."""
        return VertexGenerator.point()



    def setup_reco(self):
        #SECTION TAKEN FROM MILLIPEDE_WILKS:
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
            effectivedistancetabletmod = tmod_spline)

        self.muon_service = None

    
    
        
    

    @staticmethod
    @icetray.traysegment
    def prepare_frames(tray, name, logger, **kwargs) -> None:
        #CURRENTLY USING THE VHESELFVETO FROM MILLIPEDE WILKS FOR CONSISTENCY, CAN CHANGE THIS IF NEEDED
        #Generates the vertex seed for the initial scan.
        # Only run if HESE_VHESelfVeto is not present in the frame.
        # VertexThreshold is 250 in the original HESE analysis (Tianlu)
        # If HESE_VHESelfVeto is already in the frame, is likely using implicitly a VertexThreshold of 250 already. To be determined when this is not the case.
        def extract_seed(frame):
            seed_prefix = "HESE_VHESelfVeto"
            frame[cfg.INPUT_POS_NAME] = frame[seed_prefix + "VertexPos"]
            frame[cfg.INPUT_TIME_NAME] = frame[seed_prefix + "VertexTime"]

        tray.Add(extract_seed, "ExtractSeed", If = lambda frame: frame.Has("HESE_VHESelfVeto"))

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

    #OTHER METHODS FROM MILLIPEDE_WILKS:
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
            SaturationWindows='SaturationWindows')



        #I like having frame objects in there even if they are empty for some frames
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
            all_pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, pulses)
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




    #SEPARATE METHODS FROM REC_TAU.PY:
    def sane(frame, split_names):
        for split_name in split_names:
            if which_split(split_name=split_name)(frame):
                return True
        return False


    '''def print_frameid(frame):
    eventid = frame['I3EventHeader'].event_id
    print("*******Currently processing frame %s*******" %eventid)'''


    def fixed_dir(filelist, isdata, hypo, split_names, nframes=None):
        truths = []

        def extract(frame):
            truths.append(frame['cc'].dir)
        tray = I3Tray()
        tray.Add('I3Reader', Filenamelist=filelist)
        tray.Add(sane, split_names=split_names)
        if isdata:
            tray.Add(druth, hypo=hypo)
        else:
            tray.Add(truth, hypo=hypo)
        tray.Add(extract)
        if nframes is None:
            tray.Execute()
        else:
            tray.Execute(nframes)
        if len(set([(_.zenith, _.azimuth) for _ in truths])) != 1:
            icetray.logging.log_warn(
                'The number of extracted, unique true dirs is not 1, not updating stepXYZ')
            return None
        return truths[0]

    


    @staticmethod
    #TRAYSEGMENT MODIFIED FROM MAIN OF REC_TAU.PY
    @icetray.traysegment
    #USING MILLIPEDE WILKS FORMAT FOR ARGUMENTS OF THE FUNCTION
    def traysegment(self,tray, name, logger, seed):
        
        #TAKEN FROM MILLIPEDE_WILKS:
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







        #BEGIN REC_TAU
        wrapperfn = TaupedeWrapper
        specifier = 'TaupedeFit'
        loss_vector_suffix = 'Particles'
        #STARTING WITH THE DEFAULT ITERATIONS NUMBER
        iterations = 2
        #TOOK OUT THE TRAY INITIALIZATION AND ADDING I3 READER SO THAT THAT CAN BE DONE SEPARATELY
        #USED DEFAULT FOR SPLIT NAMES
        tray.Add(sane, split_names=['InIceSplit',])
        #tray.Add(print_frameid)
        
        #CODE TO RUN WHEN ISDATA=NONE
        tray.Add(truth, hypo="tau", If=lambda frame: not frame.Has('cc'))

        #LEAVING OUT SEED CHAIN FOR NOW


            
        #LEAVING OUT PULSE CLEANING EXCLUDED DOMS SINCE THOSE ARE IN SEPARATE METHODS IN MILLIPEDE_WILKS
        #SETTING PULSES FOR RECO TO DEFAULT
        pulses_for_reco='SplitInIcePulses'
        millipede_params = {'Pulses': f'{pulses_for_reco}PulseCleaned',
            'CascadePhotonicsService': self.cascade_service,
            'MuonPhotonicsService': None,
            'ExcludedDOMs': self.excludedDOMs,
            'ReadoutWindow': f'{pulses_for_reco}PulseCleanedTimeRange',
            'PartialExclusion': True,
            'PhotonsPerBin': 0,
            'UseUnhitDOMs': not False,
            'MinTimeWidth': 16,
            'BinSigma': np.nan,
            'RelUncertainty': 0.05,'StepZenith':0,'StepAzimuth':0}
        icetray.logging.log_info(pformat(millipede_params),
                             __name__)
        minis = [_ for _ in ['MIGRAD',
            'iMIGRAD',
            'SIMPLEX',
            'iSIMPLEX',
            'LBFGSB']] 
        sfx='PPB0'
        for mini in minis:

            tray.Add(wrapperfn,
                 f'{mini}_{PPB0}',
                 Seed=Seed,
                 Minimizer=mini,
                 Unfold=False,
                 Chain=1,
                 Iterations=iterations,
                 **millipede_params)
            seeder = lilliput.segments.add_seed_service(
                tray,
                millipede_params['Pulses'],
                [f'{specifier}_{mini}_{PPB0}'])
            minispec = mini.lower()
        relerr=0.05
        minispec += f'.relerr{relerr:.2f}'

        prefs = [_ for tup in [[f'TaupedeFit_{mini}_{PPB0}', f'MonopodFit_{mini}_{PPB0}'] for mini in minis] for _ in tup]
        tray.Add(preferred,
             i3_particles_fitparams=[(_, f'{_}FitParams') for _ in prefs],
             If=lambda f: len(prefs) > 0 and any([f.Has(_) for _ in prefs]))


        #print( prefs )

        #print("running HESE, with printing modules")      
        from segments.MillipedeWrapper import MillipedeWrapper
            
        # energy definition
        gcdfilepath = "/cvmfs/icecube.opensciencegrid.org/data/GCD/GeoCalibDetectorStatus_2020.Run134142.Pass2_V0.i3.gz"
        gcdfile = dataio.I3File(gcdfilepath)
        frame = gcdfile.pop_frame()

        while 'I3Geometry' not in frame:
            frame = gcdfile.pop_frame()
        geometry = frame['I3Geometry'].omgeo

        strings = [1, 2, 3, 4, 5, 6, 13, 21, 30, 40, 50, 59, 67, 74, 73, 72, 78, 77, 76, 75, 68, 60, 51, 41, 31, 22, 14, 7]

        outerbounds = {}
        cx, cy = [], []
        for string in strings:
            omkey = icetray.OMKey(string, 1)
            #if geometry.has_key(omkey):
            x, y = geometry[omkey].position.x, geometry[omkey].position.y
            outerbounds[string] = (x, y)
            cx.append(x)
            cy.append(y)
        cx, cy = np.asarray(cx), np.asarray(cy)
        order = np.argsort(np.arctan2(cx, cy))
        outeredge_x = cx[order]
        outeredge_y = cy[order]

        #print(sfx)


        #SHOULD I TAKE THIS OUT SINCE ITS TRACK
        #track reco
        tray.Add('I3OMSelection<I3RecoPulseSeries>', 'omselection_HESE',
            InputResponse = 'SRT' + "SplitInIcePulses",
            OmittedStrings = [79,80,81,82,83,84,85,86], # deepcore strings
            OutputOMSelection = f'SRTSplitInIcePulses_BadOMSelectionString_{sfx}',
            OutputResponse = f"SRTSplitInIcePulses_IC_Singles_{sfx}")

        tray.Add(SPEFit, f'SPEFit16_{sfx}',
            Pulses = f"SRTSplitInIcePulses_IC_Singles_{sfx}",
            Iterations = 16)

        del millipede_params["PhotonsPerBin"] # also input to MillipedeWrapper next, gives error if entered twice

    
        #HESE millipede
        tray.Add(MillipedeWrapper, f'HESEMillipedeFit_{sfx}',
            seed_cascade = f'MonopodFit_iMIGRAD_{sfx}', 
            seed_tau = f'TaupedeFit_iMIGRAD_{sfx}',
            seed_track =  f'SPEFit16_{sfx}',
            PhotonsPerBin = 0,
            ShowerSpacing = 5,
            innerboundary=550,
            outerboundary=650,
            outeredge_x=outeredge_x,
            outeredge_y=outeredge_y,
            **millipede_params)


        #rename
        tray.Add('Rename', 
             Keys=['SRTSplitInIcePulses_IC_Singles', f'SRTSplitInIcePulses_IC_Singles_{sfx}',
                   'PreferredFit_key', f'PreferredFit_key_{sfx}',
                   'PreferredFit', f"PreferredFit_{sfx}"])
        #LEAVING FINAL ORPHAN STREAM DROPPING AND FILE SAVING FOR WHEN YOU CALL THE FUNCTION FOR NOW

        def notify1(frame):
            logger.debug(f"reco complete! {datetime.datetime.now()}")

        tray.AddModule(notify1, "notify1")

    @staticmethod
    def to_recopixelvariation(frame: I3Frame, geometry: I3Frame) -> RecoPixelVariation:
        return RecoPixelVariation(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel_id=frame[cfg.I3FRAME_PIXEL].value,
            llh=frame["Dummy_llh"].value,
            reco_losses_inside=random.random(),
            reco_losses_total=random.random(),
            posvar_id=frame[cfg.I3FRAME_POSVAR].value,
            position=frame["Dummy_pos"],
            time=frame["Dummy_time"].value,
            energy=frame["Dummy_time"].value)


# Provide a standard alias for the reconstruction class provided by this module.
RECO_CLASS: Final[type[RecoInterface]] = MonoTau
