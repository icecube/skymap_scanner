"""prepare the GCDQp packet by adding frame objects that might be missing."""


# fmt: off
# pylint: skip-file

import copy
import logging
import os
from typing import List, Union

from icecube import icetray  # type: ignore[import-not-found]
from icecube import (  # type: ignore[import-not-found]  # for I3LCPulseCleaning  # noqa: F401
    DomTools,
)
from icecube.frame_object_diff.segments import (  # type: ignore[import-not-found]
    uncompress,
)
from icecube.BadDomList.BadDomListTraySegment import BadDomList # type: ignore[import-not-found]
from icecube.icetray import I3Tray  # type: ignore[import-not-found]

from .. import recos

LOGGER = logging.getLogger(__name__)


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


def prepare_frames(frame_array,
                   event_metadata,
                   baseline_GCD: Union[None, str],
                   reco_algo: str,
                   realtime_format_version: str) -> List[icetray.I3Frame]: # type hint using list available from python 3.11

    # ACTIVATE FOR DEBUG
    # icetray.logging.console()

    # Reconstruction algorithm provider class
    RecoAlgo = recos.get_reco_interface_object(reco_algo)

    output_frames: list[icetray.I3Frame] = []

    tray = I3Tray()
    tray.AddModule(FrameArraySource, Frames=frame_array)

    if baseline_GCD is not None:
        base_GCD_path, base_GCD_filename = os.path.split(baseline_GCD)
        tray.Add(uncompress, "GCD_uncompress",
                 keep_compressed=True,
                 base_path=base_GCD_path,
                 base_filename=base_GCD_filename)

    if 'BadDomsList' not in frame_array[2]:
        # rebuild the BadDomsList
        # For real data events, query i3live
        # Ignore the Snapshot export which may not exist for active realtime runs
        LOGGER.warning('BadDomsList missing in DetectorStatus frame... rebuilding. Use icetray 1.9.1 or higher to extract it directly from an existing i3 file.')
        LOGGER.info(f'Frame keys are {frame_array[2].keys()}')
        tray.Add(BadDomList,
                 RunId=event_metadata.run_id,
                 Simulation=not event_metadata.is_real_event,
                 I3liveUrlSnapshotExport=None)

    # Separates pulses in HLC and SLC to obtain the HLC series.
    # HLC pulses are used for the determination of the vertex.
    tray.AddModule('I3LCPulseCleaning', 'lcclean1',
        Input=RecoAlgo.get_input_pulses(realtime_format_version),
        OutputHLC=RecoAlgo.get_input_pulses(realtime_format_version)+'HLC',
        OutputSLC=RecoAlgo.get_input_pulses(realtime_format_version)+'SLC',
        If=lambda frame: RecoAlgo.get_input_pulses(realtime_format_version)+'HLC' not in frame)

    # Run reco-specific preprocessing.
    tray.AddSegment(
        RecoAlgo(realtime_format_version).prepare_frames,
        f"{reco_algo}_prepareframes",
        logger=LOGGER
    )

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
