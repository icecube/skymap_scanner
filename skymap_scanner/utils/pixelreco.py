"""Tools for representing a pixel reconstruction."""


import dataclasses as dc
from typing import Any, Dict, Tuple

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
        reco_algo: cfg.RecoAlgo,
    ) -> "PixelReco":
        """Get a PixelReco instance by parsing the I3Frame."""

        # import(s) that are dependent on icecube
        from .load_scan_state import get_reco_losses_inside

        # Calculate reco losses, based on load_scan_state()
        reco_losses_inside, reco_losses_total = get_reco_losses_inside(
            p_frame=frame, g_frame=geometry, reco_algo=reco_algo
        )

        if reco_algo == cfg.RecoAlgo.MILLIPEDE:
            if "MillipedeStarting2ndPass_millipedellh" not in frame:
                llh = float("nan")
            else:
                llh = frame["MillipedeStarting2ndPass_millipedellh"].logl
            return PixelReco(
                nside=frame[cfg.I3FRAME_NSIDE].value,
                pixel=frame[cfg.I3FRAME_PIXEL].value,
                llh=llh,
                reco_losses_inside=reco_losses_inside,
                reco_losses_total=reco_losses_total,
                pos_var_index=frame[cfg.I3FRAME_POSVAR].value,
                position=frame["MillipedeStarting2ndPass"].pos,
                time=frame["MillipedeStarting2ndPass"].time,
                energy=frame["MillipedeStarting2ndPass"].energy,
            )
        # elif ...:  # TODO (FUTURE DEV) - add other algos/traysegments
        #     pass
        else:
            raise RuntimeError(
                f"Requested unsupported reconstruction algorithm: {reco_algo}"
            )


NSidesDict = Dict[int, Dict[int, PixelReco]]
