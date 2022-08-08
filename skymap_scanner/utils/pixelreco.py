"""Tools for representing a pixel reconstruction."""


import dataclasses as dc
from typing import Any, Tuple

from .. import config as cfg

try:  # these are only used for typehints, so mock imports are fine
    import icecube.dataclasses as i3dataclasses  # type: ignore[import]
    from icecube.icetray import I3Frame  # type: ignore[import]
except ImportError:
    i3dataclasses = Any
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
    position: i3dataclasses.I3Position
    time: float
    energy: float

    def __post_init__(self) -> None:
        self.id_tuple = (self.nside, self.pixel, self.pos_var_index)
