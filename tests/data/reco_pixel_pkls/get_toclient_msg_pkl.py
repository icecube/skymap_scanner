"""Recreate the from-server / to-client message from a pframe."""

import argparse
import pickle
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Recreate the from-server / to-client message from a pframe"
    )

    parser.add_argument(
        "--pframe-pkl",
        help="The pframe pkl file",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--reco-algo",
        help="The reconstruction algorithm",
        required=True,
        type=str,
    )
    args = parser.parse_args()

    with open(args.pframe_pkl, "rb") as f:
        pframe = pickle.load(f)

    with open(args.pframe_pkl.parent / "in.pkl", "wb") as f:
        pickle.dump({"pframe": pframe, "reco_algo": args.reco_algo}, f)


if __name__ == "__main__":
    main()
