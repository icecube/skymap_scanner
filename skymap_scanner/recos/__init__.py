"""Tools for conducting & representing a pixel reconstruction."""


import importlib
import pkgutil
from typing import TYPE_CHECKING, Any, List

from .vertex_gen import VertexGenerator

if TYPE_CHECKING:  # https://stackoverflow.com/a/65265627
    from ..utils.pixel_classes import RecoPixelVariation

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

    # List of spline file basenames required by the class.
    # The spline files will be looked up in pre-defined local paths or fetched from a remote data store.
    SPLINE_REQUIREMENTS: List[str] = list()

    # List of vectors referenced to the origin that will be used to generate the vertex position variation.
    VERTEX_VARIATIONS: List[I3Position] = VertexGenerator.point()

    @staticmethod
    def prepare_frames(tray, name, logger, **kwargs: Any) -> None:
        raise NotImplementedError()

    @staticmethod
    def traysegment(tray, name, logger, **kwargs: Any) -> None:
        raise NotImplementedError()

    @staticmethod
    def to_recopixelvariation(
        frame: I3Frame, geometry: I3Frame
    ) -> "RecoPixelVariation":
        raise NotImplementedError()


def get_all_reco_algos() -> List[str]:
    """Return all the supported reco algorithms."""
    return [
        mi.name for mi in pkgutil.iter_modules([__file__.rsplit("/", maxsplit=1)[0]])
    ]


def get_reco_interface_object(name: str) -> RecoInterface:
    """Dynamically import the reco sub-module's class.
    Implicitly assumes that name `foo_bar` corresponds to class `FooBar`.
    """
    try:
        # Fetch module
        module = importlib.import_module(f"{__name__}.{name.lower()}")
        # Build the class name (i.e. reco_algo -> RecoAlgo).
        return getattr(module, "".join(x.capitalize() for x in name.split("_")))
    except ModuleNotFoundError as e:
        if name not in get_all_reco_algos():
            # checking this in 'except' allows us to use 'from e'
            raise UnsupportedRecoAlgoException(name) from e
        raise  # something when wrong AFTER accessing sub-module


def get_reco_spline_requirements(name: str) -> List[str]:
    try:
        module = importlib.import_module(f"{__name__}.{name.lower()}")
        return getattr(module, "spline_requirements")
    except ModuleNotFoundError as e:
        if name not in get_all_reco_algos():
            # checking this in 'except' allows us to use 'from e'
            raise UnsupportedRecoAlgoException(name) from e
        raise  # something when wrong AFTER accessing sub-module
