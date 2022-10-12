import pickle
import sys

with open(sys.argv[1], "rb") as f:
    pframe = pickle.load(f)["pframe"]

with open("new.pkl", "wb") as f:
    pickle.dump({"pframe": pframe, "reco_algo": "millipede"}, f)
