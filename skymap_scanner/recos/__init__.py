"""Tools for conducting & representing a pixel reconstruction."""


import dataclasses as dc
import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .. import config as cfg

try:  # these are only used for typehints, so mock imports are fine
    from icecube.dataclasses import I3Position  # type: ignore[import]
    from icecube.icetray import I3Frame  # type: ignore[import]
except ImportError:
    I3Position = Any
    I3Frame = Any


def pixel_to_tuple(pixel: I3Frame) -> Tuple[int, int, int]:
    """Get a tuple representing a pixel PFrame for logging."""
    return (
        pixel[cfg.I3FRAME_NSIDE].value,
        pixel[cfg.I3FRAME_PIXEL].value,
        pixel[cfg.I3FRAME_POSVAR].value,
    )


@dc.dataclass
class PixelReco:
    """A *lightweight* dataclass representing a pixel reconstruction."""

    nside: int
    pixel: int
    llh: float
    reco_losses_inside: float
    reco_losses_total: float
    pos_var_index: int
    id_tuple: Tuple[int, int, int] = dc.field(init=False, repr=False)
    position: I3Position
    time: float
    energy: float

    def __post_init__(self) -> None:
        self.id_tuple = (self.nside, self.pixel, self.pos_var_index)

    @staticmethod
    def from_i3frame(
        frame: I3Frame,
        geometry: I3Frame,
        reco_algo: str,
    ) -> "PixelReco":
        """Get a PixelReco instance by parsing the I3Frame."""
        return get_reco_interface_object(reco_algo).to_pixelreco(frame, geometry)


NSidesDict = Dict[int, Dict[int, PixelReco]]


class UnsupportedRecoAlgoException(Exception):
    """Raise when a reconstruction algorithm is not supported for a given
    operation."""

    def __init__(self, reco_algo: str):
        super().__init__(f"Requested unsupported reconstruction algorithm: {reco_algo}")


class RecoInterface:
    """An abstract class encapsulating reco-specific logic."""

    @staticmethod
    def traysegment(tray, name, logger, **kwargs: Any) -> None:
        raise NotImplementedError()

    @staticmethod
    def to_pixelreco(frame: I3Frame, geometry: I3Frame) -> PixelReco:
        raise NotImplementedError()


def get_all_reco_algos() -> List[str]:
    """Return all the supported reco algorithms."""
    return [
        mi.name for mi in pkgutil.iter_modules([__file__.rsplit("/", maxsplit=1)[0]])
    ]


def get_reco_interface_object(name: str) -> RecoInterface:
    """Dynamically import the reco sub-module's class."""
    try:
        module = importlib.import_module(f"{__name__}.{name.lower()}")
        return getattr(module, name.capitalize())
    except ModuleNotFoundError as e:
        if name not in get_all_reco_algos():
            # checking this in 'except' allows us to use 'from e'
            raise UnsupportedRecoAlgoException(name) from e
        raise  # something when wrong AFTER accessing sub-module
