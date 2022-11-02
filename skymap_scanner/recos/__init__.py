"""Tools for conducting & representing a pixel reconstruction."""


import dataclasses as dc
import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from .. import config as cfg

if TYPE_CHECKING:  # https://stackoverflow.com/a/65265627
    from ..utils.pixelreco import PixelReco

try:  # these are only used for typehints, so mock imports are fine
    from icecube.dataclasses import I3Position  # type: ignore[import]
    from icecube.icetray import I3Frame  # type: ignore[import]
except ImportError:
    I3Position = Any
    I3Frame = Any


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
    def to_pixelreco(frame: I3Frame, geometry: I3Frame) -> "PixelReco":
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
        return getattr(module, ''.join(x.capitalize() for x in name.split('_')))
    except ModuleNotFoundError as e:
        if name not in get_all_reco_algos():
            # checking this in 'except' allows us to use 'from e'
            raise UnsupportedRecoAlgoException(name) from e
        raise  # something when wrong AFTER accessing sub-module
