"""IceTray segment for a dummy reco (will crash w/in a given probability)."""


import random
from typing import Final

from ..config import ENV
from . import RecoInterface, dummy


class CrashDummy(dummy.Dummy):
    """Logic for a dummy reco."""

    def traysegment(tray, name, logger, **kwargs):
        """Perform dummy reco."""
        dummy.Dummy.traysegment(tray, name, logger, **kwargs)

        def crash(frame):
            rand = random.random()
            logger.debug(f"crash probability: {ENV.SKYSCAN_CRASH_DUMMY_PROBABILITY=}")

            if rand < ENV.SKYSCAN_CRASH_DUMMY_PROBABILITY:
                logger.debug(f"crash! {rand=}")

                # now, pick what to fail with
                fail = random.choice(["infinite-loop", "error"])
                if fail == "infinite-loop":
                    while True:  # to infinity!
                        continue
                elif fail == "error":
                    raise KeyError("intentional crash-dummy error")

            else:
                logger.debug(f"no crash: {rand=}")

        tray.AddModule(crash, "crash")


# Provide a standard alias for the reconstruction class provided by this module.
RECO_CLASS: Final[type[RecoInterface]] = CrashDummy
