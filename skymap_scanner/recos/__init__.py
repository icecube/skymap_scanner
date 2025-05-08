"""Tools for conducting & representing a pixel reconstruction."""

from abc import ABC, abstractmethod
import importlib
import pkgutil
from typing import TYPE_CHECKING, Any, List, Tuple, Union

if TYPE_CHECKING:  # https://stackoverflow.com/a/65265627
    from ..utils.pixel_classes import RecoPixelVariation

from .. import config as cfg
from ..utils.data_handling import DataStager

try:  # these are only used for typehints, so mock imports are fine
    from icecube.dataclasses import I3Position  # type: ignore[import]
    from icecube.icetray import I3Frame  # type: ignore[import]
    from icecube import astro  # type: ignore[import]
except ImportError:  # type: ignore[import]
    I3Position = Any
    I3Frame = Any

# Redundant imports are used to declare symbols exported by the module.
from .common.vertex_gen import VertexGenerator as VertexGenerator  # noqa: F401

__all__ = ["VertexGenerator"]


class UnsupportedRecoAlgoException(Exception):
    """Raise when a reconstruction algorithm is not supported for a given
    operation."""

    def __init__(self, reco_algo: str):
        super().__init__(f"Requested unsupported reconstruction algorithm: {reco_algo}")


class RecoInterface(ABC):
    """An abstract class encapsulating reco-specific logic."""

    name: str = __name__

    # List of spline filenames required by the class.
    # The spline files will be looked up in pre-defined local paths or fetched from a remote data store.
    SPLINE_REQUIREMENTS: List[str] = list()

    @abstractmethod
    def __init__(self, realtime_format_version: str):
        self.realtime_format_version = realtime_format_version

        # Reco-specific behaviors that need to be defined in derived classes.
        self.rotate_vertex: bool
        self.refine_time: bool
        self.add_fallback_position: bool

        # Optionally these can be set in derived classes for directed scans
        self.ang_dist: float = cfg.DEFAULT_ANG_DIST
        self.pointing_dir_name: Union[None, str] = None

    @staticmethod
    def get_datastager():
        datastager = DataStager(
            local_dirs=cfg.LOCAL_DATA_SOURCES,
            local_subdir=cfg.LOCAL_SPLINE_SUBDIR,
            remote_url_path=f"{cfg.REMOTE_DATA_SOURCE}/{cfg.REMOTE_SPLINE_SUBDIR}",
        )
        return datastager

    @staticmethod
    def get_input_pulses(realtime_format_version: str) -> str:
        return cfg.INPUT_KEY_NAMES_MAP.get(
            realtime_format_version, cfg.DEFAULT_INPUT_KEY_NAMES
        ).pulseseries

    @staticmethod
    @abstractmethod
    def get_vertex_variations() -> List[I3Position]:
        """Returns a list of vectors referenced to the origin that will be used to generate the vertex position variation."""
        pass

    @abstractmethod
    def prepare_frames(self, tray, name, **kwargs) -> None:
        pass

    @abstractmethod
    def setup_reco(self):
        """Performs the necessary operations to prepare the execution of the reconstruction traysegment.

        This method is expected to perform "expensive" operations such as fetching spline data and initializing IceTray spline services.
        """
        pass

    @abstractmethod
    def traysegment(self, tray, name, logger, **kwargs: Any) -> None:
        """Performs the reconstruction."""
        pass

    @staticmethod
    @abstractmethod
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


def set_pointing_ra_dec(
    particle_name: Union[str, None], p_frame: I3Frame
) -> Union[Tuple[float, float], None]:
    """Retrieves the direction for a pointed scan"""
    if particle_name is None:
        # this is the case for generic full sky scans
        return None

    if particle_name in p_frame.keys():
        pointing_dir = p_frame[particle_name].dir
        pointing_ra_dec = astro.dir_to_equa(
            pointing_dir.zenith,
            pointing_dir.azimuth,
            p_frame["I3EventHeader"].start_time.mod_julian_day_double,
        )
        return pointing_ra_dec
    raise RuntimeError(
        f"Particle {particle_name} needed for pointing was not found in the frame!"
    )
