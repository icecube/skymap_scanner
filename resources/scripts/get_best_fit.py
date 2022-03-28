#!/usr/bin/env python

# fmt: off
# isort: skip_file

import os
import numpy

from I3Tray import I3Units
from icecube import icetray, dataclasses, dataio
from icecube import gulliver, millipede

from skymap_scanner import load_cache_state

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    # get the file stager instance
    stagers = dataio.get_stagers()

    # do the work
    eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=options.CACHEDIR)

    # print "got:", eventID, state_dict
    
    best_llh = None
    best_energy = None
    best_pix = None
    best_nside = None
    for nside in list(state_dict['nsides'].keys()):
        for pixel, pixel_data in state_dict["nsides"][nside].items():
            llh = pixel_data['llh']
            energy = pixel_data['recoLossesInside']
            if best_llh is None or llh < best_llh:
                best_llh = llh
                best_pix = pixel
                best_nside = nside
                best_energy = energy
    
    print("best-fit pixel: nside =", best_nside, ", best_pix =", best_pix, ", best_llh =", best_llh, ", best_energy =", best_energy/I3Units.TeV, "TeV")
