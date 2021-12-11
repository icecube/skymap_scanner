from __future__ import print_function
from __future__ import absolute_import

import re
import copy

from icecube import icetray, dataclasses, dataio

def clean_old_frame_objects(frame_packet):
    frame_packet = [ copy.copy(frame) for frame in frame_packet ]

    # things to keep
    keep_regexs = {
        icetray.I3Frame.Physics : [
            "^FilterMask$",
            "^I3EventHeader$",
            # "^SplitInIceDSTPulses.*",
            "^SplitUncleanedInIcePulses.*",
            "^SplitInIcePulses.*",
        ],
        icetray.I3Frame.DAQ : [
            "^.*$"
        ]
    }
    
    # compile the regexps
    new_keep_regexs={}
    for i in keep_regexs.keys():
        new_keep_regexs[i.id] = [re.compile(k) for k in keep_regexs[i]]
    keep_regexs = new_keep_regexs
    
    
    for frame in frame_packet:
        if frame.Stop.id in keep_regexs:
            regexs = keep_regexs[frame.Stop.id]
            
            # see if any of them apply
            old_keys = frame.keys()
            for key in old_keys:
                keep=False
                for r in regexs:
                    if r.match(key):
                        keep=True
                        break
            
                if not keep:
                    frame.Rename(key, '__old__/'+key)

    return frame_packet
