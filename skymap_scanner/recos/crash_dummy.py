"""IceTray segment for a dummy reco (will crash w/in a given probability)."""

import os
import random
import time
from typing import Final

from icecube import icetray  # type: ignore[import]  # noqa: F401

from . import RecoInterface, dummy


class CrashDummy(dummy.Dummy):
    """Logic for a dummy reco."""

    @staticmethod
    @icetray.traysegment
    def traysegment(tray, name, logger, **kwargs):
        """Perform dummy reco."""
        dummy.Dummy.traysegment(tray, name, logger, **kwargs)

        def crash(frame):
            rand = random.random()
            prob = float(os.getenv("_SKYSCAN_CI_CRASH_DUMMY_PROBABILITY", 0.5))
            logger.debug(f"crash probability: {prob}")

            if rand < prob:
                logger.debug(f"crash! {rand=}")

                # now, pick what to fail with
                fail = random.choice(["infinite-loop", "error"])
                logger.debug(f"crashing with '{fail}'")
                if fail == "infinite-loop":
                    while True:  # to infinity!
                        time.sleep(1)
                        continue
                elif fail == "error":
                    raise KeyError("intentional crash-dummy error")

            else:
                logger.debug(f"no crash: {rand=}")

        tray.AddModule(crash, "crash")


# Provide a standard alias for the reconstruction class provided by this module.
RECO_CLASS: Final[type[RecoInterface]] = CrashDummy
