"""
prepare the GCDQp packet by adding frame objects that might be missing
"""

# fmt: off
# pylint: skip-file

import copy
import os

import numpy
from I3Tray import I3Tray, I3Units  # type: ignore[import]
from icecube import icetray  # type: ignore[import]
from icecube.frame_object_diff.segments import uncompress  # type: ignore[import]
from typing import Union, List


from .. import config as cfg
# from .. import recos
from . import LOGGER


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

        self.frame_store.append(frame)

        self.PushFrame(frame)

def prepare_frames(frame_array, baseline_GCD: Union[None, str], reco_algo: str, pulsesName: str) -> List[icetray.I3Frame]:
    # type hint using list available from python 3.11
    from icecube import (
        DomTools,
        VHESelfVeto,
        dataclasses,
        gulliver,
        millipede,
        photonics_service,
        recclasses,
        simclasses,
    )

    # ACTIVATE FOR DEBUG
    icetray.logging.console()

    output_frames: list[icetray.I3Frame] = []

    tray = I3Tray()
    tray.AddModule(FrameArraySource, Frames=frame_array)

    if baseline_GCD is not None:
        base_GCD_path, base_GCD_filename = os.path.split(baseline_GCD)
        tray.Add(uncompress, "GCD_uncompress",
                 keep_compressed=True,
                 base_path=base_GCD_path,
                 base_filename=base_GCD_filename)

    # Separates pulses in HLC and SLC to obtain the HLC series.
    # HLC pulses are used for the determination of the vertex.
    tray.AddModule('I3LCPulseCleaning', 'lcclean1',
        Input=pulsesName,
        OutputHLC=pulsesName+'HLC',
        OutputSLC=pulsesName+'SLC',
        If=lambda frame: pulsesName+'HLC' not in frame)

    # Generates the vertex seed for the initial scan. 
    # Only run if HESE_VHESelfVeto is not present in the frame.
    # VertexThreshold is 250 in the original HESE analysis (Tianlu)
    # If HESE_VHESelfVeto is already in the frame, is likely using implicitly a VertexThreshold of 250 already. To be determined when this is not the case.
    if reco_algo.lower() == 'millipede_original':
        # TODO: documentation for this conditional statement
        tray.AddModule('VHESelfVeto', 'selfveto',
                       VertexThreshold=2,
                       Pulses=pulsesName+'HLC',
                       OutputBool='HESE_VHESelfVeto',
                       OutputVertexTime=cfg.INPUT_TIME_NAME,
                       OutputVertexPos=cfg.INPUT_POS_NAME,
                       If=lambda frame: "HESE_VHESelfVeto" not in frame)
    else:
        tray.AddModule('VHESelfVeto', 'selfveto',
            VertexThreshold=250,
            Pulses=pulsesName+'HLC',
            OutputBool='HESE_VHESelfVeto',
            OutputVertexTime=cfg.INPUT_TIME_NAME,
            OutputVertexPos=cfg.INPUT_POS_NAME,
            If=lambda frame: "HESE_VHESelfVeto" not in frame)

        # this only runs if the previous module did not return anything
        tray.AddModule('VHESelfVeto', 'selfveto-emergency-lowen-settings',
                       VertexThreshold=5,
                       Pulses=pulsesName+'HLC',
                       OutputBool='VHESelfVeto_meaningless_lowen',
                       OutputVertexTime=cfg.INPUT_TIME_NAME,
                       OutputVertexPos=cfg.INPUT_POS_NAME,
                       If=lambda frame: not frame.Has("HESE_VHESelfVeto"))
        
    # if reco_algo.lower() == "splinempe":
    #     # perform fit
    #     tray.AddSegment(
    #         recos.get_reco_interface_object(reco_algo).prepare_frames,
    #         f"{reco_algo}_prepareframes",
    #         logger=LOGGER
    #     )

    # If the event has a GCD diff (compressed GCD), only keep the diffs.
    # The GCD will be reassembled from baseline + diff by the client.
    if baseline_GCD is not None:
        # The input event carries a compressed GCD.
        # Only the GCD diff is propagated, the full GCD will be rebuilt downstream.
        def delFrameObjectsWithDiffsAvailable(frame):
            all_keys = list(frame.keys())
            for key in list(frame.keys()):
                if not key.endswith('Diff'): continue
                non_diff_key = key[:-4]
                if non_diff_key in all_keys:
                    del frame[non_diff_key]
                    LOGGER.debug(f"Deleted {non_diff_key} from frame because a corresponding Diff exists.")
        tray.AddModule(delFrameObjectsWithDiffsAvailable, "delFrameObjectsWithDiffsAvailable", Streams=[icetray.I3Frame.Geometry, icetray.I3Frame.Calibration, icetray.I3Frame.DetectorStatus])

    tray.AddModule(FrameArraySink, FrameStore=output_frames)
    tray.AddModule("TrashCan")
    tray.Execute()
    tray.Finish()
    del tray

    return output_frames
