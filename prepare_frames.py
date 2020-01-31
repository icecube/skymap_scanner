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

    nominalPulsesName = "SplitInIcePulses"

    # sanity check the packet
    if frame_packet[-1].Stop != icetray.I3Frame.Physics and frame_packet[-1].Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("frame packet does not end with Physics frame")

    # move the last packet frame from Physics to the Physics stream temporarily
    frame_packet[-1] = rewrite_frame_stop(frame_packet[-1], icetray.I3Frame.Stream('P'))

    output_frames = []

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
        Pulses=nominalPulsesName+'HLC',
        OutputBool='HESE_VHESelfVeto',
        OutputVertexTime='HESE_VHESelfVetoVertexTime',
        OutputVertexPos='HESE_VHESelfVetoVertexPos',
        If=lambda frame: "HESE_VHESelfVeto" not in frame)

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

    # move the last packet frame from Physics to the 'p' stream
    output_frames[-1] = rewrite_frame_stop(output_frames[-1], icetray.I3Frame.Stream('p'))

    return output_frames
