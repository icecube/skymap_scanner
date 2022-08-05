"""Reco a single pixel."""

# pylint: skip-file

import argparse
import datetime
import logging
import os
import pickle
from pathlib import Path
from typing import Any, List

from I3Tray import I3Tray  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    dataio,
    frame_object_diff,
    icetray,
    photonics_service,
)
from icecube.frame_object_diff.segments import uncompress  # type: ignore[import]
from wipac_dev_tools import logging_tools

from .. import config
from ..load_scan_state import get_baseline_gcd_frames, get_reco_losses_inside
from ..utils import PixelReco, pixel_to_tuple, save_GCD_frame_packet_to_file
from .millipede_traysegment import millipede_traysegment

LOGGER = logging.getLogger("skyscan-client-reco")


def frame_for_logging(frame: icetray.I3Frame) -> str:
    return f"{repr(frame)}/{frame}"


class LoadInitialFrames(icetray.I3Module):  # type: ignore[misc]
    """Push Pixel PFrame into tray along with GCDQp frames."""

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        self.AddParameter("Pixel", "Pixel PFrame", None)
        self.AddParameter("GCDQpFrames", "GCDQp packet (list of frames)", [])

        self._frames_loaded = False

    def Configure(self) -> None:
        self.pixel = self.GetParameter("Pixel")
        if not self.pixel:
            raise RuntimeError("self.pixel is not set")

        self.GCDQp_packet = self.GetParameter("GCDQpFrames")
        if not self.GCDQp_packet:
            raise RuntimeError("self.GCDQp_packet is empty")

    def Process(self) -> None:
        """Push the given frames."""
        if self.PopFrame():
            raise RuntimeError("LoadInitialFrames needs to be used as a driving module")

        if self._frames_loaded:  # are we done yet?
            self.RequestSuspension()
            return

        for frame in self.GCDQp_packet:
            LOGGER.debug(f"Pushing GCDQP Frame: {frame_for_logging(frame)}")
            self.PushFrame(frame)

        LOGGER.debug(f"Pushing Pixel Frame: {frame_for_logging(self.pixel)}")
        self.PushFrame(self.pixel)

        self._frames_loaded = True


def get_pixelreco(
    baseline_GCD_file: str,
    GCDQp_packet: List[icetray.I3Frame],
    frame: icetray.I3Frame,
) -> PixelReco:
    """Get self as a PixelReco instance."""

    # Calculate reco losses, based on load_scan_state()
    # apparently baseline GCD is sufficient here
    # maybe filestager can be None
    geometry = get_baseline_gcd_frames(
        baseline_GCD_file, GCDQp_packet, filestager=dataio.get_stagers()
    )[0]

    try:
        reco_losses_inside, reco_losses_total = get_reco_losses_inside(
            p_frame=frame, g_frame=geometry
        )
    except KeyError as e:
        LOGGER.error(f"Missing attribute in Geometry frame: {e}")
        LOGGER.info(f"Frame contains the following keys {geometry.keys()}")
        raise

    return PixelReco(
        nside=frame["SCAN_HealpixNSide"].value,
        pixel=frame["SCAN_HealpixPixel"].value,
        llh=frame["PixelReco_llh"].value,
        reco_losses_inside=reco_losses_inside,
        reco_losses_total=reco_losses_total,
        pos_var_index=frame["SCAN_PositionVariationIndex"].value,
        position=frame["PixelReco_position"],
        time=frame["PixelReco_time"].value,
        energy=frame["PixelReco_energy"].value,
    )


def save_to_disk_cache(frame: icetray.I3Frame, save_dir: Path) -> Path:
    """Save this frame to the disk cache."""
    nside = frame["SCAN_HealpixNSide"].value
    pixel = frame["SCAN_HealpixPixel"].value

    nside_dir = save_dir / "nside{0:06d}".format(nside)
    nside_dir.mkdir(parents=True, exist_ok=True)

    pixel_file_name = nside_dir / "pix{0:012d}.i3".format(pixel)

    save_GCD_frame_packet_to_file([frame], str(pixel_file_name))
    return pixel_file_name


def get_GCD_diff_base_handle(baseline_GCD_file: str) -> Any:
    """Find an available GCD base path."""
    stagers = dataio.get_stagers()

    # try to load the base file from the various possible input directories
    GCD_diff_base_handle = None
    if baseline_GCD_file not in [None, "None"]:
        for GCD_base_dir in config.GCD_BASE_DIRS:
            try:
                read_url = os.path.join(GCD_base_dir, baseline_GCD_file)
                LOGGER.debug("reading baseline GCD from {0}".format(read_url))
                GCD_diff_base_handle = stagers.GetReadablePath(read_url)
                if not os.path.isfile(str(GCD_diff_base_handle)):
                    raise RuntimeError("file does not exist (or is not a file)")
            except:
                LOGGER.debug(" -> failed")
                GCD_diff_base_handle = None
            if GCD_diff_base_handle is not None:
                LOGGER.debug(" -> success")
                break

        if GCD_diff_base_handle is None:
            raise RuntimeError(
                "Could not read the input GCD file '{0}' from any pre-configured location".format(
                    baseline_GCD_file
                )
            )

    return GCD_diff_base_handle


def reco_pixel(
    pframe: icetray.I3Frame,
    GCDQp_packet: List[icetray.I3Frame],
    baseline_GCD_file: str,
    out_pkl: Path,
) -> Path:
    """Actually do the reco."""
    LOGGER.info(f"Reco'ing pixel: {pixel_to_tuple(pframe)}...")
    LOGGER.debug(f"PFrame: {frame_for_logging(pframe)}")
    for frame in GCDQp_packet:
        LOGGER.debug(f"GCDQP Frame: {frame_for_logging(frame)}")
    LOGGER.info(f"{baseline_GCD_file=}")

    # Constants ########################################################

    pulsesName = "SplitUncleanedInIcePulsesLatePulseCleaned"
    ExcludedDOMs = [
        "CalibrationErrata",
        "BadDomsList",
        "DeepCoreDOMs",
        "SaturatedDOMs",
        "BrightDOMs",
        pulsesName + "TimeWindows",
    ]
    SPEScale = 0.99

    # Load Data ########################################################

    # At HESE energies, deposited light is dominated by the stochastic losses
    # (muon part emits so little light in comparison)
    # This is why we can use ems_mie instead of InfBareMu_mie even for tracks
    base = os.path.expandvars("$I3_TESTDATA/photospline/ems_mie_z20_a10.%s.fits")
    for fname in [base % "abs", base % "prob"]:
        if not os.path.exists(fname):
            raise FileNotFoundError(fname)
    cascade_service = photonics_service.I3PhotoSplineService(
        base % "abs", base % "prob", timingSigma=0.0
    )
    cascade_service.SetEfficiencies(SPEScale)

    muon_service = None

    # Build Tray #######################################################

    tray = I3Tray()

    # Load frames
    tray.AddModule(
        LoadInitialFrames,
        "LoadInitialFrames",
        Pixel=pframe,
        GCDQpFrames=GCDQp_packet,
    )

    def makeSurePulsesExist(frame) -> None:
        pulsesName = "SplitUncleanedInIcePulsesLatePulseCleaned"
        if pulsesName not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName + "TimeWindows" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName + "TimeWindows"))
        if pulsesName + "TimeRange" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName + "TimeRange"))

    tray.AddModule(makeSurePulsesExist, "makeSurePulsesExist")

    def notifyStart(frame):
        LOGGER.debug(f"got data - uncompressing GCD {datetime.datetime.now()}")

    tray.AddModule(notifyStart, "notifyStart")

    # get GCD
    @icetray.traysegment
    def UncompressGCD(tray, name, base_GCD_path, base_GCD_filename):
        tray.Add(
            uncompress,
            name + "_GCD_patch",
            keep_compressed=False,
            base_path=base_GCD_path,
            base_filename=base_GCD_filename,
        )

    if GCD_diff_base_handle := get_GCD_diff_base_handle(baseline_GCD_file):
        tray.Add(
            UncompressGCD,
            "GCD_uncompress",
            base_GCD_path="",
            base_GCD_filename=str(GCD_diff_base_handle),
        )

    # TODO (FUTURE DEV) - change reco algo based on some pkl attribute
    # perform fit
    tray.AddSegment(
        millipede_traysegment,
        "millipede_traysegment",
        muon_service=muon_service,
        cascade_service=cascade_service,
        ExcludedDOMs=ExcludedDOMs,
        pulsesName=pulsesName,
        logger=LOGGER,
    )

    # Write reco out
    def writeout_reco(frame: icetray.I3Frame) -> None:
        LOGGER.debug(
            f"writeout_reco {pixel_to_tuple(frame)}: {frame_for_logging(frame)}"
        )
        if frame.Stop != icetray.I3Frame.Physics:
            LOGGER.debug("frame.Stop is not Physics")
            return
        if out_pkl.exists():
            raise FileExistsError(out_pkl)
        save_to_disk_cache(frame, out_pkl.parent)
        with open(out_pkl, "wb") as f:
            LOGGER.info(
                f"Pickle-dumping reco {pixel_to_tuple(frame)}: "
                f"{frame_for_logging(frame)} to {out_pkl}."
            )
            pixreco = get_pixelreco(baseline_GCD_file, GCDQp_packet, frame)
            LOGGER.info(f"PixelReco: {pixreco}")
            pickle.dump(pixreco, f)

    tray.AddModule(writeout_reco, "writeout_reco")

    tray.AddModule("TrashCan", "thecan")

    # Start Tray #######################################################

    LOGGER.info("Staring IceTray...")
    tray.Execute()
    tray.Finish()
    del tray
    LOGGER.info("Done with IceTray.")

    # Check Output #####################################################

    if not out_pkl.exists():
        raise FileNotFoundError(
            f"Out file was not written {pixel_to_tuple(pframe)}: {out_pkl}"
        )
    return out_pkl


# fmt: on
def main() -> None:
    """Reco a single pixel."""
    parser = argparse.ArgumentParser(
        description=(
            "Perform reconstruction on a pixel "
            "by reading `--in-pkl FILE` and writing result to "
            "`--out-pkl FILE`."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # input/output args
    parser.add_argument(
        "--in-pkl",
        required=True,
        help="a pkl file containing the pixel to reconstruct",
        type=Path,
    )
    parser.add_argument(
        "--out-pkl",
        required=True,
        help="a pkl file to write the reconstruction to",
        type=Path,
    )

    # extra "physics" args
    parser.add_argument(
        "--gcdqp-packet-pkl",
        dest="GCDQp_packet_pkl",
        required=True,
        help="a pkl file containing the GCDQp_packet (list of I3Frames)",
        type=Path,
    )
    parser.add_argument(
        "--baseline-gcd-file",
        dest="baseline_GCD_file",
        required=True,
        help="the baseline_GCD_file string",
        type=str,
    )

    # logging args
    parser.add_argument(
        "-l",
        "--log",
        default="INFO",
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default="WARNING",
        help="the output logging level for third-party loggers",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        args.log.upper(),
        first_party_loggers=[LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # get PFrame
    with open(args.in_pkl, "rb") as f:
        pframe = pickle.load(f)

    # get GCDQp_packet
    with open(args.GCDQp_packet_pkl, "rb") as f:
        GCDQp_packet = pickle.load(f)

    # go!
    reco_pixel(pframe, GCDQp_packet, args.baseline_GCD_file, args.out_pkl)
    LOGGER.info("Done reco'ing pixel.")


if __name__ == "__main__":
    main()
