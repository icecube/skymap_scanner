"""IceTray segment for a dummy reco."""

# pylint: skip-file

import datetime
import random

from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    dataclasses,
    dataio,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    millipede,
    photonics_service,
    recclasses,
    simclasses,
)

from ... import config as cfg


@icetray.traysegment
def dummy_traysegment(tray, name, logger):
    """Perform dummy reco."""

    def notify0(frame):
        logger.debug(f"starting a new fit ({name})! {datetime.datetime.now()}")

    tray.AddModule(notify0, "notify0")

    def add_vals(frame):
        frame["Dummy_llh"] = dataclasses.I3Double(random.random())
        frame["Dummy_pos"] = dataclasses.I3Position(
            random.random() * I3Units.m, 
            random.random() * I3Units.m, 
            random.random() * I3Units.m,
        )
        frame["Dummy_time"] = dataclasses.I3Double(random.random())
        frame["Dummy_energy"] = dataclasses.I3Double(random.random())

    tray.AddModule(add_vals, "add_vals")

    def notify1(frame):
        logger.debug(f"Dummy pass done! {datetime.datetime.now()}")

    tray.AddModule(notify1, "notify1")
