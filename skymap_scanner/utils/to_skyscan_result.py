"""For encapsulating the results of an event scan in a single instance."""

import dataclasses as dc
import logging
from typing import Tuple

import numpy as np
from skyreader import EventMetadata, SkyScanResult

from .pixel_classes import NSidesDict, RecoPixelFinal

LOGGER = logging.getLogger(__name__)


def from_nsides_dict(
    nsides_dict: NSidesDict,
    is_complete: bool,
    event_metadata: EventMetadata,
) -> SkyScanResult:
    """Factory method for nsides_dict."""
    event_metadata_dict = {}
    if event_metadata:
        event_metadata_dict = dc.asdict(event_metadata)

    result = {}
    for nside, pixel_dict in nsides_dict.items():
        _dtype = np.dtype(  # type: ignore[call-overload]
            SkyScanResult.PIXEL_TYPES[event_metadata.version],
            metadata=dict(
                nside=nside,
                complete=is_complete,
                **event_metadata_dict,
            ),
        )
        nside_pixel_values = np.zeros(len(pixel_dict), dtype=_dtype)
        LOGGER.debug(
            f"nside {nside} has {len(pixel_dict)} pixels / {12 * nside**2} total."
        )

        for i, (pixel_id, pixfin) in enumerate(sorted(pixel_dict.items())):
            nside_pixel_values[i] = _pixelreco_to_tuple(pixfin, nside, pixel_id)

        result[SkyScanResult.format_nside(nside)] = nside_pixel_values

    return SkyScanResult(result)


def _pixelreco_to_tuple(
    pixfin: RecoPixelFinal, nside: int, pixel_id: int
) -> Tuple[int, float, float, float, float, float, float, float]:
    if (
        not isinstance(pixfin, RecoPixelFinal)
        or nside != pixfin.nside
        or pixel_id != pixfin.pixel_id
    ):
        msg = f"Invalid {RecoPixelFinal} for {(nside,pixel_id)}: {pixfin}"
        LOGGER.error(msg)
        raise ValueError(msg)
    return (
        pixfin.pixel_id,  # index
        pixfin.llh,  # llh
        pixfin.reco_losses_inside,  # E_in
        pixfin.reco_losses_total,  # E_tot
        pixfin.position.x,  # X
        pixfin.position.y,  # Y
        pixfin.position.z,  # Z
        pixfin.time,  # time
    )
