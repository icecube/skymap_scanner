import pickle
import sys

import Path

with open(sys.argv[1], "rb") as f:
    pframe = pickle.load(f)["pframe"]

with open(Path(sys.argv[1]).parent / "new.pkl", "wb") as f:
    pickle.dump({"pframe": pframe, "reco_algo": "millipede"}, f)
