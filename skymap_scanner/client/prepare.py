"""Setup common resources for future IceTray instances of a specified
reconstruction."""


import argparse
import logging

from wipac_dev_tools import logging_tools

from .. import config as cfg
from .. import recos

LOGGER = logging.getLogger("skyscan.client.prepare")


def main() -> None:
    """Reco a single pixel."""
    parser = argparse.ArgumentParser(
        description="Setup common resources for future IceTray instances of a specified reconstruction.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # "physics" args
    parser.add_argument(
        "--reco-algo",
        required=True,
        choices=recos.get_all_reco_algos(),
        help="The reconstruction algorithm prepare for",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        cfg.ENV.SKYSCAN_LOG,  # type: ignore[arg-type]
        first_party_loggers="skyscan",
        third_party_level=cfg.ENV.SKYSCAN_LOG_THIRD_PARTY,  # type: ignore[arg-type]
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # go!
    RecoAlgo = recos.get_reco_interface_object(args.reco_algo)
    reco = RecoAlgo()
    reco.setup_reco()


if __name__ == "__main__":
    main()
    LOGGER.info("Done.")
