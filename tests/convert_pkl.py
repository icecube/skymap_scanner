"""A script to help when a pickle format changes.

The should be used as a one-off script & updated as needed.
"""

import dataclasses as dc  # noqa: F401
import pickle
import sys

from icecube.dataclasses import I3Position  # type: ignore[import]  # noqa: F401
from icecube.icetray import I3Frame  # type: ignore[import]  # noqa: F401

OUT_PKL_FPATH = sys.argv[1]  # "/local/pkls/1660761104.474899.out.pkl"
with open(OUT_PKL_FPATH, "rb") as f:
    pixfin = pickle.load(f)
    print(pixfin)
with open(OUT_PKL_FPATH, "wb") as f:
    pickle.dump(
        {"pixfin": pixfin["pixfin"], "runtime": 65},
        f,
    )
