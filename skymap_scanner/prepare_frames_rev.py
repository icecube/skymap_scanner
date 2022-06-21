# fmt: off
# pylint: skip-file

"""
prepare the GCDQp packet for millipede

# code adapted from python/prepare_frames.py 
"""

from I3Tray import I3Tray


from python_io import ListReader, ListWriter
from millipede_prep import millipede_prep

import logging

logger = logging.getLogger(__name__)


"""
Main function
"""     
def prepare_frames(frame_array, GCD_diff_base_filename, pulsesName="SplitUncleanedInIcePulses"):

    output_frames = list()
    
    tray = I3Tray()

    tray.AddModule(ListReader, Frames=frame_array)

    ExcludedDOMs = tray.AddSegment(millipede_prep, "millipede_prep", GCD_diff_base_filename=GCD_diff_base_filename, pulsesName=pulsesName)

    tray.AddModule(ListWriter, FrameStore=output_frames)

    tray.Execute()

    del tray
    
    return (output_frames, ExcludedDOMs)
