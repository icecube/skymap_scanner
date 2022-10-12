import pickle
import sys
from pathlib import Path

with open(sys.argv[1], "rb") as f:
    pframe = pickle.load(f)["pframe"]

with open(Path(sys.argv[1]).parent / "new.pkl", "wb") as f:
    pickle.dump({"pframe": pframe, "reco_algo": "millipede"}, f)

with open(Path(sys.argv[1]).parent / "just-pframe.pkl", "wb") as f:
    pickle.dump(pframe, f)
