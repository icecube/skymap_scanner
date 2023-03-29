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


PixelRecoID = Tuple[int, int, int]


def pframe_to_pixelrecoid(pixel: I3Frame) -> PixelRecoID:
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
    position: I3Position
    time: float
    energy: float

    @staticmethod
    def from_recopixelvariation(reco_pixvar: "RecoPixelVariation") -> "PixelReco":
        """Effectively removes the position variation id."""
        return PixelReco(
            nside=reco_pixvar.nside,
            pixel=reco_pixvar.pixel,
            llh=reco_pixvar.llh,
            reco_losses_inside=reco_pixvar.reco_losses_inside,
            reco_losses_total=reco_pixvar.reco_losses_total,
            position=reco_pixvar.position,
            time=reco_pixvar.time,
            energy=reco_pixvar.energy,
        )


@dc.dataclass
class RecoPixelVariation(PixelReco):
    """A dataclass representing a pixel-variation reconstruction."""

    pos_var_index: int
    id_tuple: PixelRecoID = dc.field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.id_tuple = (self.nside, self.pixel, self.pos_var_index)

    @staticmethod
    def from_i3frame(
        frame: I3Frame,
        geometry: I3Frame,
        reco_algo: str,
    ) -> "RecoPixelVariation":
        """Get a PixelReco instance by parsing the I3Frame."""
        return recos.get_reco_interface_object(reco_algo).to_recopixelvariation(
            frame, geometry
        )


NSidesDict = Dict[int, Dict[int, PixelReco]]  # nside:(id:PixelReco}
