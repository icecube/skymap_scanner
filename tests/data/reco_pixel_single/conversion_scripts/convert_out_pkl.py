"""A script to help when a pickle format changes.

The should be used as a one-off script & updated as needed.
"""

import base64
import dataclasses as dc  # noqa: F401
import json
import pickle
import sys
from pathlib import Path

from icecube.dataclasses import I3Position  # type: ignore[import]  # noqa: F401
from icecube.icetray import I3Frame  # type: ignore[import]  # noqa: F401

OUT_PKL_FPATH = sys.argv[1]  # "/local/test-data/1660761104.474899.out.pkl"
with open(OUT_PKL_FPATH, "rb") as f:
    msg = pickle.load(f)
    print(msg)
with open(Path(OUT_PKL_FPATH).parent / "out.json", "w") as f:
    print(msg.items())
    json.dump(
        {
            "reco_pixel_variation_pkl_b64": base64.b64encode(
                pickle.dumps(msg["reco_pixel_variation"])
            ).decode(),
            "runtime": msg["runtime"],
        },
        f,
        indent=4,
    )
