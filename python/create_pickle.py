# fmt: off
# isort: skip_file

import os
import pickle
from icecube import dataio
from skymap_scanner.load_scan_state import load_cache_state

def parse_scan(cache_dir, eventID):
    stagers = dataio.get_stagers()
    eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=cache_dir)
    output_dir = "{0}/summary_pickle/".format(cache_dir)

    try:
        os.makedirs(output_dir)
    except OSError:
        pass
    output_path = "{0}/{1}.pkl".format(output_dir, eventID)
    print(("Saving to {0}".format(output_path)))
    with open(output_path, "w") as f:
        pickle.dump(state_dict["nsides"], f)

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")

    (options,args) = parser.parse_args()

    if len(args) > 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    elif len(args) == 1:
        eventIDs = [args[0]]
    else:
        eventIDs = [x for x in os.listdir(options.CACHEDIR)]

    for eventID in eventIDs:
        try:
            parse_scan(options.CACHEDIR, eventID)
        except RuntimeError:
            print(("Skipping {0} due to RuntimeError".format(eventID)))
