#!/usr/bin/env python

import os
import numpy

from I3Tray import I3Units
from icecube import icetray, dataclasses, dataio
from icecube import gulliver, millipede

from icecube.skymap_scanner import load_cache_state

def get_best_fit_v2(eventID, cache_dir, log_func=None):
    
    if log_func is None:
        def log_func(x):
            print(x)

    # get the file stager instance                                                          
    stagers = dataio.get_stagers()

    # do the work                                                                          
    eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=cache_dir)
    
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
    
    #text = "best-fit pixel: nside =" + str(best_nside) + ", best_pix =" + str(best_pix) + ", best_llh =" + str(best_llh) + ", best_energy =" + str(best_energy/I3Units.TeV) + "TeV"
    text = "The best-fit pixel is `" + os.path.join(cache_dir, eventID, "nside{0:06d}".format(best_nside), "pix{0:012d}.i3".format(best_pix)) 
    text += "` with best-fit energy = {0:.2f} TeV".format(best_energy/I3Units.TeV) 
    log_func(text)

    #print "best-fit pixel: nside =", best_nside, ", best_pix =", best_pix, ", best_llh =", best_llh, ", best_energy =", best_energy/I3Units.TeV, "TeV"

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

    get_best_fit_v2(eventID, options.CACHEDIR)

    
