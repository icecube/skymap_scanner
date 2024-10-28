"""Classes for representing a pixel-like things in various forms."""

import dataclasses as dc
import time
from typing import Any, Dict, Tuple

from .. import config as cfg
from .. import recos

try:  # these are only used for typehints, so mock imports are fine
    from icecube.dataclasses import I3Position  # type: ignore[import]
    from icecube.icetray import I3Frame  # type: ignore[import]
except ImportError:
    I3Position = Any
    I3Frame = Any


PTuple = Tuple[int, int, int]


def pframe_tuple(pixel: I3Frame) -> PTuple:
    """Get a tuple representing a pixel PFrame for logging."""
    return (
        pixel[cfg.I3FRAME_NSIDE].value,
        pixel[cfg.I3FRAME_PIXEL].value,
        pixel[cfg.I3FRAME_POSVAR].value,
    )


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class _PixelLike:
    """The most basic data needed to represent a pixel-like thing."""

    nside: int
    pixel_id: int


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class SentPixelVariation(_PixelLike):
    """Used for tracking a single sent pixel variation."""

    nside: int
    pixel_id: int
    posvar_id: int
    sent_time: float = dc.field(compare=False)  # compare also excludes field from hash

    @staticmethod
    def from_pframe(pframe: I3Frame) -> "SentPixelVariation":
        """Get an instance from a Pframe."""
        return SentPixelVariation(
            nside=pframe[cfg.I3FRAME_NSIDE].value,
            pixel_id=pframe[cfg.I3FRAME_PIXEL].value,
            posvar_id=pframe[cfg.I3FRAME_POSVAR].value,
            sent_time=time.time(),
        )

    def matches_reco_pixel_variation(self, reco_pixvar: "RecoPixelVariation") -> bool:
        """Does this match the RecoPixelFinal instance?"""
        return (
            self.nside == reco_pixvar.nside
            and self.pixel_id == reco_pixvar.pixel_id
            and self.posvar_id == reco_pixvar.posvar_id
        )


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class _RecoData:
    """Data that's computing during a reco."""

    llh: float
    reco_losses_inside: float
    reco_losses_total: float
    position: I3Position
    time: float
    energy: float


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class RecoPixelFinal(_PixelLike, _RecoData):
    """A representation of a final saved pixel post-reco.

    This is separate from _RecoData so can strong-type the two w/ mypy.
    """

    @staticmethod
    def from_recopixelvariation(reco_pixvar: "RecoPixelVariation") -> "RecoPixelFinal":
        """Effectively removes the position variation id."""
        return RecoPixelFinal(
            nside=reco_pixvar.nside,
            pixel_id=reco_pixvar.pixel_id,
            llh=reco_pixvar.llh,
            reco_losses_inside=reco_pixvar.reco_losses_inside,
            reco_losses_total=reco_pixvar.reco_losses_total,
            position=reco_pixvar.position,
            time=reco_pixvar.time,
            energy=reco_pixvar.energy,
        )


@dc.dataclass(frozen=True, eq=True)  # frozen + eq makes instances hashable
class RecoPixelVariation(_PixelLike, _RecoData):
    """A dataclass representing a pixel-variation reconstruction."""

    posvar_id: int
    id_tuple: PTuple = dc.field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(  # b/c frozen
            self, "id_tuple", (self.nside, self.pixel_id, self.posvar_id)
        )

    @staticmethod
    def from_i3frame(
        frame: I3Frame,
        geometry: I3Frame,
        reco_algo: str,
    ) -> "RecoPixelVariation":
        """Get a RecoPixelFinal instance by parsing the I3Frame."""
        return recos.get_reco_interface_object(reco_algo).to_recopixelvariation(
            frame, geometry
        )


NSidesDict = Dict[int, Dict[int, RecoPixelFinal]]  # nside:(id:RecoPixelFinal}
