"""Tools for conducting & representing a pixel reconstruction."""


import importlib
import pkgutil
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:  # https://stackoverflow.com/a/65265627
    from ..utils.pixel_classes import RecoPixelVariation

from .. import config as cfg
from ..utils.data_handling import DataStager

try:  # these are only used for typehints, so mock imports are fine
    from icecube.dataclasses import I3Position  # type: ignore[import]
    from icecube.icetray import I3Frame  # type: ignore[import]
except ImportError:
    I3Position = Any
    I3Frame = Any

# Redundant import(s) to declare exported symbol(s).
from .common.vertex_gen import VertexGenerator as VertexGenerator


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

    def init(self):
        raise NotImplementedError()

    @staticmethod
    def get_vertex_variations() -> List[I3Position]:
        """Returns a list of vectors referenced to the origin that will be used to generate the vertex position variation."""
        raise NotImplementedError()

    @staticmethod
    def do_rotate_vertex() -> bool:
        """Defines whether each generated vertex variation should be rotated along the axis of the scan direction. With the exception for legacy algorithms (MillipedeOriginal) this should typycally return True."""
        return True

    @staticmethod
    def do_refine_time() -> bool:
        """Defines whether to refine seed time."""
        return True

    @staticmethod
    def prepare_frames(tray, name, **kwargs) -> None:
        raise NotImplementedError()

    def setup_reco(self):
        """Performs the necessary operations to prepare the execution of the reconstruction traysegment."""
        raise NotImplementedError()

    def get_datastager(self):
        datastager = DataStager(
            local_paths=cfg.LOCAL_DATA_SOURCES,
            local_subdir=cfg.LOCAL_SPLINE_SUBDIR,
            remote_path=f"{cfg.REMOTE_DATA_SOURCE}/{cfg.REMOTE_SPLINE_SUBDIR}",
        )
        return datastager

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


def get_reco_interface_object(name: str) -> type[RecoInterface]:
    """Dynamically import the reco sub-module's class."""
    try:
        # Fetch module
        module = importlib.import_module(f"{__name__}.{name.lower()}")
        return module.RECO_CLASS
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
