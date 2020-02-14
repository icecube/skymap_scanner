"""
prepare the GCDQp packet by adding frame objects that might be missing
"""

from __future__ import print_function
from __future__ import absolute_import

import copy
import math
import os
import numpy
import json

import config
from utils import rewrite_frame_stop

from icecube import icetray, dataclasses
from icecube.frame_object_diff.segments import uncompress
from I3Tray import I3Tray, I3Units

class FrameArraySource(icetray.I3Module):
    def __init__(self, ctx):
        super(FrameArraySource, self).__init__(ctx)
        self.AddParameter("Frames",
            "The frames to push to modules downstream",
            [])
        self.AddOutBox("OutBox")

    def Configure(self):
        self.frames = copy.copy(self.GetParameter("Frames"))

    def Process(self):
        # driving module
        if self.PopFrame():
            raise RuntimeError("FrameArrayReader needs to be used as a driving module")

        if len(self.frames) == 0:
            # queue is empty
            self.RequestSuspension()
            return

        self.PushFrame(self.frames.pop(0)) # push the frontmost item


class FrameArraySink(icetray.I3Module):
    def __init__(self, ctx):
        super(FrameArraySink, self).__init__(ctx)
        self.AddParameter("FrameStore",
            "Array to which to add frames",
            [])
        self.AddOutBox("OutBox")

    def Configure(self):
        self.frame_store = self.GetParameter("FrameStore")

    def Process(self):
        frame = self.PopFrame()
        if not frame: return

        # ignore potential TrayInfo frames
        if frame.Stop == icetray.I3Frame.TrayInfo:
            self.PushFrame(frame)
            return

        frame_copy = copy.copy(frame)
        frame_copy.purge()
        self.frame_store.append(frame_copy)
        del frame_copy

        self.PushFrame(frame)

from icecube.realtime_gfu.muon_alerts import gfu_alert_eval
from icecube.realtime_hese.HESE_alerts_v2 import hese_alert_eval

def check_alerts(frame):
    alert_dict = json.loads(frame["AlertShortFollowupMsg"].value)
    alert_dict = {'value': {'data': alert_dict}}
    
    gfu_val = gfu_alert_eval(alert_dict)
    hese_val = hese_alert_eval(alert_dict)

    if (gfu_val is not None and gfu_val['pass_tight'] == True):
        #print 'This is a GOLD GFU alert'
        alert_pass = 'gfu-gold'
    elif (hese_val is not None and hese_val['pass_tight'] == True):
        #print 'This is a GOLD HESE alert'
        alert_pass = 'hese-gold'
    elif (gfu_val is not None and gfu_val['pass_loose'] == True):
        #print 'This is a BRONZE GFU alert'
        alert_pass = 'gfu-bronze'
    elif (hese_val is not None and hese_val['pass_loose'] == True):
        #print 'This is a BRONZE HESE alert'
        alert_pass = 'hese-bronze'
        return results
    else:
        #print 'No Bronze or gold alerts found'
        alert_pass = 'none'

    frame["AlertPassed"] = dataclasses.I3String(alert_pass)

    if gfu_val is not None:
        gfu_val  = {k : float(v) for k, v in gfu_val.iteritems()}
    else:
        gfu_val = {}
    frame["AlertInfoGFU"] = dataclasses.I3MapStringDouble(gfu_val)

    if hese_val is not None:
        hese_val = {k : float(v) for k, v in hese_val.iteritems()}
    else:
        hese_val = {}
    frame["AlertInfoHESE"] = dataclasses.I3MapStringDouble(hese_val)

    return frame


def recreate_alert_short_followup_msg(frame_packet, pulsesName="SplitInIcePulses"):
    from icecube import dataclasses, recclasses, simclasses
    from icecube import filterscripts
    from icecube.filterscripts.muonfilter import MuonFilter
    from icecube.filterscripts.onlinel2filter import OnlineL2Filter
    from icecube.filterscripts.hesefilter import HeseFilter
    from icecube.filterscripts.highqfilter import HighQFilter
    from icecube.filterscripts.gfufilter import GammaFollowUp
    from icecube.filterscripts.alerteventfollowup import AlertEventFollowup
    icetray.load("DomTools", False)

    SplineDir                = '/opt/i3-data/photon-tables/splines/'
    SplineRecoAmplitudeTable = os.path.join(SplineDir, 'InfBareMu_mie_abs_z20a10.fits')
    SplineRecoTimingTable    = os.path.join(SplineDir, 'InfBareMu_mie_prob_z20a10.fits')

    nominalPulsesName = "SplitInIcePulses"

    # sanity check the packet
    if frame_packet[-1].Stop != icetray.I3Frame.Physics and frame_packet[-1].Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("frame packet does not end with Physics frame")

    # move the last packet frame from Physics to the Physics stream temporarily
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('P'))

    output_frames = []

    icetray.set_log_level_for_unit('I3Tray', icetray.I3LogLevel.LOG_WARN)

    tray = I3Tray()
    tray.AddModule(FrameArraySource, Frames=frame_packet)

    tray.Add(uncompress, "GCD_uncompress",
             keep_compressed=True,
             base_path=config.base_GCD_path)

    if pulsesName != nominalPulsesName:
        def copyPulseName(frame, old_name, new_name):
            mask = dataclasses.I3RecoPulseSeriesMapMask(frame, old_name)
            if new_name in frame:
                print("** WARNING: {0} was already in frame. overwritten".format(new_name))
                del frame[new_name]
            frame[new_name] = mask
            frame[new_name+"TimeRange"] = copy.deepcopy(frame[old_name+"TimeRange"])
        tray.AddModule(copyPulseName, "copyPulseName",
            old_name=pulsesName,
            new_name=nominalPulsesName)

    # many of the filters check if the SMT8 trigger fired. Assume it did
    def AddInIceSMTTriggeredBool(frame):
        frame['InIceSMTTriggered'] = icetray.I3Bool(True)
    tray.Add(AddInIceSMTTriggeredBool, "AddInIceSMTTriggeredBool", Streams=[icetray.I3Frame.DAQ])

    ##################### below is cut from BaseProcessing ###################

    from icecube import STTools
    from icecube import linefit, lilliput
    import icecube.lilliput.segments

    # first, perform the pulse cleaning that yields "CleanedMuonPulses"
    from icecube.STTools.seededRT.configuration_services import I3DOMLinkSeededRTConfigurationService
    seededRTConfig = I3DOMLinkSeededRTConfigurationService(
                         ic_ic_RTRadius              = 150.0*I3Units.m,
                         ic_ic_RTTime                = 1000.0*I3Units.ns,
                         treat_string_36_as_deepcore = False,
                         useDustlayerCorrection      = False,
                         allowSelfCoincidence        = True
                     )
    tray.AddModule('I3SeededRTCleaning_RecoPulseMask_Module', 'seededrt',
        InputHitSeriesMapName  = nominalPulsesName,
        OutputHitSeriesMapName = nominalPulsesName + "_RTC",
        STConfigService        = seededRTConfig,
        SeedProcedure          = 'HLCCoreHits',
        NHitsThreshold         = 2,
        MaxNIterations         = 3,
        Streams                = [icetray.I3Frame.Physics],
    )

    tray.AddModule("I3TimeWindowCleaning<I3RecoPulse>", "TimeWindowCleaning",
        InputResponse = nominalPulsesName + "_RTC",
        OutputResponse = nominalPulsesName + "_TWRTC",
        TimeWindow = 6000*I3Units.ns,
        )

    tray.AddModule("I3FirstPulsifier", "first-pulsify",
        InputPulseSeriesMapName = nominalPulsesName + "_TWRTC",
        OutputPulseSeriesMapName = 'FirstPulseMuonPulses',
        KeepOnlyFirstCharge = False,   # default
        UseMask = False,               # default
        )

    tray.AddSegment(linefit.simple, "imprv_LF", 
        inputResponse = nominalPulsesName + "_TWRTC", 
        fitName = 'PoleMuonLinefit',
        )

    tray.AddSegment(lilliput.segments.I3SinglePandelFitter, 'PoleMuonLlhFit',
        seeds   = ['PoleMuonLinefit'],
        pulses  = nominalPulsesName + "_TWRTC",
        fitname = 'PoleMuonLlhFit',
        )

    ##################### above is cut from BaseProcessing ###################

    # re-run all necessary filters
    tray.AddSegment(MuonFilter, "MuonFilter",
        pulses = nominalPulsesName + "_TWRTC",
        If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
        )
   
   # High Q filter
    tray.AddSegment(HighQFilter, "HighQFilter",
        pulses = nominalPulsesName,
        If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
        )

    # HESE veto (VHESelfVeto)
    tray.AddSegment(HeseFilter, "HeseFilter",
        pulses = nominalPulsesName,
        If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
        )
    
    # OnlineL2, used by HESE and GFU
    tray.AddSegment(OnlineL2Filter, "OnlineL2",
        pulses = nominalPulsesName + "_TWRTC",
        linefit_name = 'PoleMuonLinefit',
        llhfit_name = 'PoleMuonLlhFit',
        SplineRecoAmplitudeTable = SplineRecoAmplitudeTable,
        SplineRecoTimingTable = SplineRecoTimingTable,
        PathToCramerRaoTable = None,
        forceOnlineL2BadDOMList = None,
        If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
        )

    tray.AddSegment(GammaFollowUp, "GammaFollowUp",
        OnlineL2SegmentName = "OnlineL2",
        pulses = nominalPulsesName + "_TWRTC",
        BDTUpFile = None,
        BDTDownFile = None,
        angular_error = True,
        If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
        )

    # we do not necessarily have launches, so EHE is practically impossible. Skip EHE alerts.
    # from icecube.filterscripts.ehefilter import EHEFilter
    # from icecube.filterscripts.ehealertfilter import EHEAlertFilter
    # tray.AddSegment(EHEFilter, "EHEFilter")
    # tray.AddSegment(EHEAlertFilter, "EHEAlertFilter",
    #     pulses = nominalPulsesName + "_TWRTC",
    #     # If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
    #     )

    # finally, create "AlertShortFollowupMsg"
    tray.AddSegment(AlertEventFollowup, "AlertFollowup",
        omit_GCD_diff = True,
        If = lambda frame: frame.Stop == icetray.I3Frame.Physics # work around stupidity in the filter's If=<...> statements
        )
        
    # the previous module also creates "AlertFullFollowupMsg" but we do not need it
    def cleanupFullFollowupMessage(frame):
        if "AlertFullFollowupMsg" in frame:
            del frame["AlertFullFollowupMsg"]
    tray.Add(cleanupFullFollowupMessage, "cleanupFullFollowupMessage")

    def delFrameObjectsWithDiffsAvailable(frame):
        all_keys = frame.keys()
        for key in frame.keys():
            if not key.endswith('Diff'): continue
            non_diff_key = key[:-4]
            if non_diff_key in all_keys:
                del frame[non_diff_key]
                # print("deleted", non_diff_key, "from frame because a Diff exists")
    tray.AddModule(delFrameObjectsWithDiffsAvailable, "delFrameObjectsWithDiffsAvailable", Streams=[icetray.I3Frame.Geometry, icetray.I3Frame.Calibration, icetray.I3Frame.DetectorStatus])

    tray.AddModule(FrameArraySink, FrameStore=output_frames)
    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray

    icetray.set_log_level_for_unit('I3Tray', icetray.I3LogLevel.LOG_NOTICE)
    
    return output_frames[-1]["AlertShortFollowupMsg"]
    
    
def calculate_online_alert_dict(frame_packet, pulsesName="SplitInIcePulses", always_recreate_alert_short_followup_msg=True):
    # create the frame packet we return
    out_frame_packet = [copy.copy(frame) for frame in frame_packet]

    if always_recreate_alert_short_followup_msg:
        if "AlertShortFollowupMsg" in out_frame_packet[-1]:
            print("Replacing existing \"AlertShortFollowupMsg\" in input...")
            out_frame_packet[-1].Rename("AlertShortFollowupMsg", "__old__/AlertShortFollowupMsg")
        else:
            print("Frame object \"AlertShortFollowupMsg\" not found. Recreating it...")
        
    if "AlertShortFollowupMsg" not in out_frame_packet[-1]:
        # we need to run a lot of L1 to re-create the "AlertShortFollowupMsg"
        if not always_recreate_alert_short_followup_msg:
            print("Frame object \"AlertShortFollowupMsg\" not found. Recreating it...")
        msg = recreate_alert_short_followup_msg(frame_packet, pulsesName=pulsesName)
        out_frame_packet[-1]["AlertShortFollowupMsg"] = msg
        print("\"AlertShortFollowupMsg\" recreated.")

    # check which alerts passed and add a corresponding frame object
    out_frame_packet[-1] = check_alerts(out_frame_packet[-1])

    print("")
    print("")
    print(" ** Alert type: {}".format(out_frame_packet[-1]["AlertPassed"].value))
    print("")
    print(" ** GFU:  {}".format(out_frame_packet[-1]["AlertInfoGFU"]))
    print("")
    print(" ** HESE: {}".format(out_frame_packet[-1]["AlertInfoHESE"]))
    print("")
    print("")


    return out_frame_packet
