"""A script to help when a pickle format changes.

The should be used as a one-off script & updated as needed.
"""

import dataclasses as dc  # noqa: F401
import pickle
import sys

from icecube.dataclasses import I3Position  # type: ignore[import]  # noqa: F401
from icecube.icetray import I3Frame  # type: ignore[import]  # noqa: F401
from skymap_scanner.utils.pixel_classes import RecoPixelVariation

OUT_PKL_FPATH = sys.argv[1]  # "/local/pkls/1660761104.474899.out.pkl"
with open(OUT_PKL_FPATH, "rb") as f:
    msg = pickle.load(f)
    print(msg)
with open(OUT_PKL_FPATH, "wb") as f:
    print(msg.items())
    pickle.dump(
        {
            "reco_pixel_variation": RecoPixelVariation(
                nside=msg["pixreco"].nside,
                pixel_id=msg["pixreco"].pixel,
                posvar_id=msg["pixreco"].pos_var_index,
                llh=msg["pixreco"].llh,
                reco_losses_inside=msg["pixreco"].reco_losses_inside,
                reco_losses_total=msg["pixreco"].reco_losses_total,
                position=msg["pixreco"].position,
                time=msg["pixreco"].time,
                energy=msg["pixreco"].energy,
            ),
            "runtime": 65,
        },
        f,
    )
