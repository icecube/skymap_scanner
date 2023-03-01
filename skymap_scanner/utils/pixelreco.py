"""Tools for representing a pixel reconstruction."""


import dataclasses as dc
from typing import Any, Dict, Tuple

from .. import config as cfg
from .. import recos

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
        reco_obj: recos.RecoInterface,
    ) -> "PixelReco":
        """Get a PixelReco instance by parsing the I3Frame."""
        return reco_obj.to_pixelreco(frame, geometry)


NSidesDict = Dict[int, Dict[int, PixelReco]]
