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
    pixreco = pickle.load(f)
    print(pixreco)
with open(OUT_PKL_FPATH, "wb") as f:
    pickle.dump(
        {
            "pixreco": pixreco,
            "start": 0,
            "end": 100,
        },
        f,
    )
