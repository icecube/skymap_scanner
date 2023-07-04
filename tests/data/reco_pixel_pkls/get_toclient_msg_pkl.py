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

    # When extracting the debug .pkl from ewms-pilot, the in- pickles already contain the full message.
    # Do we need to support "bare" pframes pickles at all?
    # For the moment, this is a workaround.
    if "pframe" in pframe:
        # Effectively this is equivalent to copying the file.
        with open(args.pframe_pkl.parent / "in.pkl", "wb") as f:
            pickle.dump(pframe, f)
    else:
        with open(args.pframe_pkl.parent / "in.pkl", "wb") as f:
            pickle.dump({"pframe": pframe, "reco_algo": args.reco_algo}, f)


if __name__ == "__main__":
    main()
