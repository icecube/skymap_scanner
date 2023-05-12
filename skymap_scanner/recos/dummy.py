"""IceTray segment for a dummy reco."""


import datetime
import random
import time
from typing import List, Final

from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    dataclasses,
    frame_object_diff,
    gulliver,
    gulliver_modules,
    icetray,
    millipede,
    photonics_service,
    recclasses,
    simclasses,
)
from icecube.icetray import I3Frame  # type: ignore[import]

from .. import config as cfg
from ..utils.pixel_classes import RecoPixelVariation
from ..utils.data_handling import DataStager
from . import RecoInterface


class Dummy(RecoInterface):
    """Logic for a dummy reco."""

    def __init__(self):
        pass

    def setup_reco(self):
        pass

    @staticmethod
    @icetray.traysegment
    def traysegment(tray, name, logger, **kwargs):
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
            time.sleep(random.uniform(1, 3))

        tray.AddModule(add_vals, "add_vals")

        def notify1(frame):
            logger.debug(f"Dummy pass done! {datetime.datetime.now()}")

        tray.AddModule(notify1, "notify1")

    @staticmethod
    def to_recopixelvariation(frame: I3Frame, geometry: I3Frame) -> RecoPixelVariation:
        return RecoPixelVariation(
            nside=frame[cfg.I3FRAME_NSIDE].value,
            pixel_id=frame[cfg.I3FRAME_PIXEL].value,
            llh=frame["Dummy_llh"].value,
            reco_losses_inside=random.random(),
            reco_losses_total=random.random(),
            posvar_id=frame[cfg.I3FRAME_POSVAR].value,
            position=frame["Dummy_pos"],
            time=frame["Dummy_time"].value,
            energy=frame["Dummy_time"].value,
        )


# Provide a standard alias for the reconstruction class provided by this module.
RECO_CLASS: Final[type[RecoInterface]] = Dummy
