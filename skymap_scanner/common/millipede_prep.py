from icecube import icetray
from icecube.frame_object_diff.segments import uncompress

# code extracted from python/prepare_frames.py 

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

import icetray

from late_pulse_cleaning import LatePulseCleaning

"""
Auxiliary function-modules
"""
def createEmptyDOMLists(frame, ListNames=list()):
    for name in ListNames:
        if name not in frame:
            frame[name] = dataclasses.I3VectorOMKey()


# TODO: review this function
def delFrameObjectsWithDiffsAvailable(frame):
    all_keys = list(frame.keys())
    for key in list(frame.keys()):
        if not key.endswith("Diff"):
            continue
        non_diff_key = key[:-4]
        if non_diff_key in all_keys:
            del frame[non_diff_key]
            # print "deleted", non_diff_key, "from frame because a Diff exists"


"""
Main segment for preparation of millipede scans
"""


@icetray.traysegment
def millipede_prep(
    tray, name, GCD_diff_base_filename, pulsesName="SplitUncleanedInIcePulses"
):

    nominalPulsesName = "SplitUncleanedInIcePulses"

    if GCD_diff_base_filename is not None:
        # to be checked when we hit this case!
        base_GCD_path, base_GCD_filename = os.path.split(GCD_diff_base_filename)
        tray.Add(
            uncompress,
            "GCD_uncompress",
            keep_compressed=True,
            base_path=base_GCD_path,
            base_filename=base_GCD_filename,
        )

    if pulsesName != nominalPulsesName:
        tray.AddModule(
            "Delete",
            "deletePulseName",
            Keys=[nominalPulsesName, nominalPulsesName + "Timerange"],
        )
        tray.AddModule(
            "Copy",
            "copyPulseName",
            Keys=[
                pulsesName,
                nominalPulsesName,
                pulsesName + "TimeRange",
                nominalPulsesName + "TimeRange",
            ],
        )

    tray.AddModule(
        "I3LCPulseCleaning",
        "lcclean1",
        Input=nominalPulsesName,
        OutputHLC=nominalPulsesName + "HLC",
        OutputSLC=nominalPulsesName + "SLC",
        If=lambda frame: nominalPulsesName + "HLC" not in frame,
    )

    tray.AddModule(
        "VHESelfVeto",
        "selfveto",
        VertexThreshold=2,
        Pulses=nominalPulsesName + "HLC",
        OutputBool="HESE_VHESelfVeto",
        OutputVertexTime="HESE_VHESelfVetoVertexTime",
        OutputVertexPos="HESE_VHESelfVetoVertexPos",
        If=lambda frame: "HESE_VHESelfVeto" not in frame,
    )

    tray.AddModule(
        "Delete",
        "cleanupFrame",
        Keys=["SaturatedDOMs", "BrightDOMs"],
        Streams=[icetray.I3Frame.DAQ, icetray.I3Frame.Physics],
    )

    exclusionList = tray.AddSegment(
        millipede.HighEnergyExclusions,
        "millipede_DOM_exclusions",
        Pulses=nominalPulsesName,
        ExcludeDeepCore="DeepCoreDOMs",
        ExcludeSaturatedDOMs="SaturatedDOMs",
        ExcludeBrightDOMs="BrightDOMs",
        BadDomsList="BadDomsList",
        CalibrationErrata="CalibrationErrata",
        SaturationWindows="SaturationWindows",
    )

    # create frame objects if they are empty for some frames
    tray.AddModule(
        createEmptyDOMLists,
        "createEmptyDOMLists",
        ListNames=["BrightDOMs"],
        Streams=[icetray.I3Frame.Physics],
    )

    # clean late pulses
    tray.AddModule(LatePulseCleaning, "LatePulseCleaning", Pulses=nominalPulsesName)

    ExcludedDOMs = exclusionList + [nominalPulsesName + "LatePulseCleanedTimeWindows"]

    if GCD_diff_base_filename is not None:
        tray.AddModule(
            delFrameObjectsWithDiffsAvailable,
            "delFrameObjectsWithDiffsAvailable",
            Streams=[
                icetray.I3Frame.Geometry,
                icetray.I3Frame.Calibration,
                icetray.I3Frame.DetectorStatus,
            ],
        )

    return ExcludedDOMs
