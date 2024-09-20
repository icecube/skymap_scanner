"""Recreate the from-server / to-client message from a pframe."""

import argparse
import base64
import json
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
        depickled = pickle.load(f)

    # When extracting the debug .pkl from ewms-pilot, the in- pickles already contain the full message.
    # Do we need to support "bare" pframes pickles at all?
    # For the moment, this is a workaround.
    if isinstance(depickled, dict):
        assert depickled["reco_algo"] == args.reco_algo
        pframe = depickled["pframe"]

    # is just a pframe!
    with open(args.pframe_pkl.parent / "in.json", "w") as f:
        json.dump(
            {
                "pframe_pkl_b64": base64.b64encode(pickle.dumps(pframe)).decode(),
                "reco_algo": args.reco_algo,
            },
            f,
        )


if __name__ == "__main__":
    main()
