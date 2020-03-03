"""
prepare the GCDQp packet by adding frame objects that might be missing
"""

from __future__ import print_function
from __future__ import absolute_import

import copy
import math
import os
import numpy

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

def prepare_frames(frame_packet, pulsesName="SplitInIcePulses"):
    from icecube import dataclasses, recclasses, simclasses
    from icecube import DomTools, VHESelfVeto
    from icecube import photonics_service, gulliver, millipede
    from i3deepice.i3module import DeepLearningModule

    nominalPulsesName = "SplitInIcePulses"

    # sanity check the packet
    if frame_packet[-1].Stop != icetray.I3Frame.Physics and frame_packet[-1].Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("frame packet does not end with Physics frame")

    # move the last packet frame from Physics to the Physics stream temporarily
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('P'))

    intermediate_frames = []

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

    tray.AddModule('I3LCPulseCleaning', 'lcclean1',
        Input=nominalPulsesName,
        OutputHLC=nominalPulsesName+'HLC',
        OutputSLC=nominalPulsesName+'SLC',
        If=lambda frame: nominalPulsesName+'HLC' not in frame)

    tray.AddModule('VHESelfVeto', 'selfveto',
        VertexThreshold=250., # 250pe is the default setting
        Pulses=nominalPulsesName+'HLC',
        OutputBool='HESE_VHESelfVeto',
        OutputVertexTime='HESE_VHESelfVetoVertexTime',
        OutputVertexPos='HESE_VHESelfVetoVertexPos',
        If=lambda frame: "HESE_VHESelfVeto" not in frame)

    def MarkFrameForSubThresholdVeto(frame):
        any_in_frame = ("HESE_VHESelfVeto" in frame) or ("HESE_VHESelfVetoVertexTime" in frame) or ("HESE_VHESelfVetoVertexPos" in frame)
        all_in_frame = ("HESE_VHESelfVeto" in frame) and ("HESE_VHESelfVetoVertexTime" in frame) and ("HESE_VHESelfVetoVertexPos" in frame)
        
        if all_in_frame:
            # all good
            frame["HESE_VertexThreshold"] = dataclasses.I3Double(250.)
        elif any_in_frame:
            print(frame)
            raise RuntimeError("Some of the HESE veto objects exist but not all of them. This is an error.")
        else:
            print(" ******* VERY LOW CHARGE EVENT - re-doing HESE veto with much lower pe vertex threshold to at least get a seed position ******* ")
            # Re-do this with 10pe, but let people looking at the resulting
            # frame know! (the resulting veto condition is basically meaningless)
            frame["HESE_VertexThreshold"] = dataclasses.I3Double(5.)
            frame["HESE_VHESelfVeto"] = icetray.I3Bool(False)
    tray.AddModule(MarkFrameForSubThresholdVeto, 'MarkFrameForSubThresholdVeto')

    # Make sure this actually calculated something - especially if we are far below the
    # veto threshold, this will silently do nothing (which is kind of expected).
    tray.AddModule('VHESelfVeto', 'selfveto-emergency-lowen-settings',
        VertexThreshold=5., # usually this is at 250pe - use a much lower setting here
        Pulses=nominalPulsesName+'HLC',
        OutputBool='HESE_VHESelfVeto_meaningless_lowen',
        OutputVertexTime='HESE_VHESelfVetoVertexTime',
        OutputVertexPos='HESE_VHESelfVetoVertexPos',
        If=lambda frame: (frame.Stop==icetray.I3Frame.Physics) and (frame["HESE_VertexThreshold"].value < 250.)) # this only runs if the previous module did not return anything
    
    def CheckHESEVertexExists(frame):
        pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, nominalPulsesName+'HLC')
        if "HESE_VHESelfVeto" not in frame:
            print(pulses)
            print(frame)
            raise RuntimeError("Cannot continue, HESE_VHESelfVeto not in frame (too low total charge?).")
        if "HESE_VHESelfVetoVertexTime" not in frame:
            print(pulses)
            print(frame)
            raise RuntimeError("Cannot continue, HESE_VHESelfVetoVertexTime not in frame (too low total charge?).")
        if "HESE_VHESelfVetoVertexPos" not in frame:
            print(pulses)
            print(frame)
            raise RuntimeError("Cannot continue, HESE_VHESelfVetoVertexPos not in frame (too low total charge?).")
    tray.AddModule(CheckHESEVertexExists, 'CheckHESEVertexExists')
        

    # make sure the script doesn't fail because some objects alreadye exist
    def cleanupFrame(frame):
        if "SaturatedDOMs" in frame:
            del frame["SaturatedDOMs"]
        # Added BrightDOMs Nov 28 2015 since it was already in frame - Will
        if "BrightDOMs" in frame:
            del frame["BrightDOMs"]

    tray.AddModule(cleanupFrame, "cleanupFrame",
        Streams=[icetray.I3Frame.DAQ, icetray.I3Frame.Physics])

    ##################

    def _weighted_quantile_arg(values, weights, q=0.5):
        indices = numpy.argsort(values)
        sorted_indices = numpy.arange(len(values))[indices]
        medianidx = (weights[indices].cumsum()/weights[indices].sum()).searchsorted(q)
        if (0 <= medianidx) and (medianidx < len(values)):
            return sorted_indices[medianidx]
        else:
            return numpy.nan

    def weighted_quantile(values, weights, q=0.5):
        if len(values) != len(weights):
            raise ValueError("shape of `values` and `weights` don't match!")
        index = _weighted_quantile_arg(values, weights, q=q)
        if not numpy.isnan(index):
            return values[index]
        else:
            return numpy.nan

    def weighted_median(values, weights):
        return weighted_quantile(values, weights, q=0.5)

    def LatePulseCleaning(frame, Pulses, Residual=3e3*I3Units.ns):
        pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, Pulses)
        mask = dataclasses.I3RecoPulseSeriesMapMask(frame, Pulses)
        counter, charge = 0, 0
        qtot = 0
        times = dataclasses.I3TimeWindowSeriesMap()
        for omkey, ps in pulses.iteritems():
            if len(ps) < 2:
                if len(ps) == 1:
                    qtot += ps[0].charge
                continue
            ts = numpy.asarray([p.time for p in ps])
            cs = numpy.asarray([p.charge for p in ps])
            median = weighted_median(ts, cs)
            qtot += cs.sum()
            for p in ps:
                if p.time >= (median+Residual):
                    if not times.has_key(omkey):
                        ts = dataclasses.I3TimeWindowSeries()
                        ts.append(dataclasses.I3TimeWindow(median+Residual, numpy.inf)) # this defines the **excluded** time window
                        times[omkey] = ts
                    mask.set(omkey, p, False)
                    counter += 1
                    charge += p.charge
        frame[nominalPulsesName+"LatePulseCleaned"] = mask
        frame[nominalPulsesName+"LatePulseCleanedTimeWindows"] = times
        frame[nominalPulsesName+"LatePulseCleanedTimeRange"] = copy.deepcopy(frame[Pulses+"TimeRange"])

    tray.AddModule(LatePulseCleaning, "LatePulseCleaning",
                    Pulses=nominalPulsesName,
                    )

    ExcludedDOMs = \
    tray.AddSegment(millipede.HighEnergyExclusions, 'millipede_DOM_exclusions',
        Pulses = pulsesName,
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
    tray.AddModule(createEmptyDOMLists, 'createEmptyDOMListsD',
        ListNames = ["BadDomsList"],
        Streams=[icetray.I3Frame.DetectorStatus])
    tray.AddModule(createEmptyDOMLists, 'createEmptyDOMListsQ',
        ListNames = ["SaturatedDOMs", "CalibrationErrata"],
        Streams=[icetray.I3Frame.DAQ])
    tray.AddModule(createEmptyDOMLists, 'createEmptyDOMListsP',
        ListNames = ["BrightDOMs"],
        Streams=[icetray.I3Frame.Physics])
    
    # add the late pulse exclusion windows
    ExcludedDOMs = ExcludedDOMs + [nominalPulsesName+'LatePulseCleaned'+'TimeWindows']

    def EnsureExlusionObjectsExist(frame, ListNames=[]):
        for name in ListNames:
            if name in frame: continue
            print(frame)
            raise RuntimeError("No frame object named \"{}\" found in frame (expected for DOM exclusions.)".format(name))
    tray.AddModule(EnsureExlusionObjectsExist, 'EnsureExlusionObjectsExist',
        ListNames = ExcludedDOMs,
        Streams=[icetray.I3Frame.Physics])
    
    tray.AddModule(FrameArraySink, FrameStore=intermediate_frames)
    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray


    print("")
    print("Starting CNN classification....")
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

    ##### DeepIceLearning has a bug that does not allow multiple instances to be used.
    ##### work around this by just re-starting a full tray
    intermediate_frames2 = []
    tray = I3Tray()
    tray.AddModule(FrameArraySource, Frames=intermediate_frames)

    tray.AddModule(DeepLearningModule, 'cnn_classification',
                    batch_size=1,
                    cpu_cores=1,
                    gpu_cores=0,
                    model='classification',
                    pulsemap=nominalPulsesName,
                    calib_errata='CalibrationErrata',
                    bad_dom_list='BadDomsList',
                    saturation_windows='SaturationWindows',
                    bright_doms='BrightDOMs',
                    save_as='CNN_classification')

    def print_classifier(frame):
        print("")
        print("CNN classification done:\n", frame["CNN_classification"])
        print("")
    tray.AddModule(print_classifier, "print_classifier")
    
    ##################

    tray.AddModule(FrameArraySink, FrameStore=intermediate_frames2)
    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray


    print("")
    print("Starting CNN energy reconstruction....")

    ##### DeepIceLearning has a bug that does not allow multiple instances to be used.
    ##### work around this by just re-starting a full tray
    output_frames_fullGCD = []
    tray = I3Tray()
    tray.AddModule(FrameArraySource, Frames=intermediate_frames2)

    tray.AddModule(DeepLearningModule, 'cnn_energy',
                    batch_size=1,
                    cpu_cores=1,
                    gpu_cores=0,
                    model='mu_energy_reco_full_range',
                    pulsemap=nominalPulsesName,
                    calib_errata='CalibrationErrata',
                    bad_dom_list='BadDomsList',
                    saturation_windows='SaturationWindows',
                    bright_doms='BrightDOMs',
                    save_as='CNN_mu_energy_reco_full_range')

    def print_energy(frame):
        print("")
        print("CNN energy reco done: {:.2f}TeV".format( (10**frame["CNN_mu_energy_reco_full_range"]['mu_E_on_entry'])/1e3) )
        print("")
    tray.AddModule(print_energy, "print_energy")
    
    ##################

    tray.AddModule(FrameArraySink, FrameStore=output_frames_fullGCD)
    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray



    print("Final cleanup of GCD objects (where a Diff is avaiable)....")

    ##### Now remove GCD objects again where a Diff is available
    output_frames = []

    tray = I3Tray()
    tray.AddModule(FrameArraySource, Frames=output_frames_fullGCD)
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

    ## we are done with preparing the frames.

    # move the last packet frame from Physics to the 'p' stream
    output_frames[-1] = rewrite_frame_stop(output_frames[-1], icetray.I3Frame.Stream('p'))

    return output_frames
