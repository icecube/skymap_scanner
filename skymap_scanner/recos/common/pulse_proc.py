from typing import Final

from icecube import dataclasses


def mask_deepcore(frame, origpulses: str, maskedpulses: str):
    """Masks DeepCore pulses by selecting string numbers."""
    FIRST_DEEPCORE_STRING: Final[int] = 79
    frame[maskedpulses] = dataclasses.I3RecoPulseSeriesMapMask(
        frame,
        origpulses,
        lambda omkey, index, pulse: omkey.string < FIRST_DEEPCORE_STRING,
    )
