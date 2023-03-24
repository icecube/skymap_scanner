"""Reco a single pixel."""

# pylint: skip-file

import argparse
import datetime
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, List, Union

from I3Tray import I3Tray  # type: ignore[import]
from icecube import (  # type: ignore[import]  # noqa: F401
    dataio,
    frame_object_diff,
    full_event_followup,
    icetray,
    photonics_service,
)
from icecube.frame_object_diff.segments import uncompress  # type: ignore[import]
from wipac_dev_tools import argparse_tools, logging_tools

from .. import config as cfg
from .. import recos
from ..utils import pixelreco
from ..utils.load_scan_state import get_baseline_gcd_frames
from ..utils.utils import save_GCD_frame_packet_to_file

LOGGER = logging.getLogger("skyscan.client.reco")


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


def save_to_disk_cache(frame: icetray.I3Frame, save_dir: Path) -> Path:
    """Save this frame to the disk cache."""
    nside_dir = save_dir / "nside{0:06d}".format(frame[cfg.I3FRAME_NSIDE].value)
    nside_dir.mkdir(parents=True, exist_ok=True)

    pixel_fname = nside_dir / "pix{0:012d}.i3".format(frame[cfg.I3FRAME_PIXEL].value)

    save_GCD_frame_packet_to_file([frame], str(pixel_fname))
    return pixel_fname


def check_baseline_GCD(baseline_GCD_file: Union[str, None]) -> bool:
    LOGGER.debug(f"Testing baseline GCD at {baseline_GCD_file}")

    if baseline_GCD_file is None:
        return False

    if os.path.isfile(baseline_GCD_file):
        return True
    else:
        raise RuntimeError(
            f"The provided baseline GCD file could not be read '{baseline_GCD_file}'. Cannot build GCD from GCD diff."
        )


def reco_pixel(
    reco_algo: str,
    pframe: icetray.I3Frame,
    GCDQp_packet: List[icetray.I3Frame],
    baseline_GCD_file: str,
    out_pkl: Path,
) -> Path:
    """Actually do the reco."""
    start_time = time.time()
    LOGGER.info(f"Reco'ing pixel: {pixelreco.pframe_to_pixelrecoid(pframe)}...")
    LOGGER.debug(f"PFrame: {frame_for_logging(pframe)}")
    for frame in GCDQp_packet:
        LOGGER.debug(f"GCDQP Frame: {frame_for_logging(frame)}")
    LOGGER.info(f"{baseline_GCD_file=}")

    # Build Tray #######################################################
    tray = I3Tray()

    # Load frames
    tray.AddModule(
        LoadInitialFrames,
        "LoadInitialFrames",
        Pixel=pframe,
        GCDQpFrames=GCDQp_packet,
    )

    def notifyStart(frame):
        LOGGER.debug(f"got data - uncompressing GCD {datetime.datetime.now()}")

    tray.AddModule(notifyStart, "notifyStart")

    # get GCD
    if check_baseline_GCD(baseline_GCD_file):
        tray.Add(
            uncompress,
            "GCD_uncompress_GCD_patch",
            keep_compressed=False,
            base_path="",
            base_filename=baseline_GCD_file,
        )

    # perform fit
    tray.AddSegment(
        recos.get_reco_interface_object(reco_algo).traysegment,
        f"{reco_algo}_traysegment",
        logger=LOGGER,
        seed=pframe[f"{cfg.OUTPUT_PARTICLE_NAME}"],
    )

    # Write reco out
    def writeout_reco(frame: icetray.I3Frame) -> None:
        LOGGER.debug(
            f"writeout_reco {pixelreco.pframe_to_pixelrecoid(frame)}: {frame_for_logging(frame)}"
        )
        if frame.Stop != icetray.I3Frame.Physics:
            LOGGER.debug("frame.Stop is not Physics")
            return
        if out_pkl.exists():  # check in case the tray is re-writing this file
            raise FileExistsError(out_pkl)
        save_to_disk_cache(frame, out_pkl.parent)
        with open(out_pkl, "wb") as f:
            LOGGER.info(
                f"Pickle-dumping reco {pixelreco.pframe_to_pixelrecoid(frame)}: "
                f"{frame_for_logging(frame)} to {out_pkl}."
            )
            geometry = get_baseline_gcd_frames(baseline_GCD_file, GCDQp_packet)[0]
            pixreco = pixelreco.PixelReco.from_i3frame(frame, geometry, reco_algo)
            LOGGER.info(f"PixelReco: {pixreco}")
            pickle.dump(
                {
                    "pixreco": pixreco,
                    # can't trust the clocks running in containers, but we can trust the relative time
                    "runtime": time.time() - start_time,
                },
                f,
            )

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
            f"Out file was not written {pixelreco.pframe_to_pixelrecoid(pframe)}: {out_pkl}"
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
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_file(),
            FileNotFoundError(x),
        ),
    )
    parser.add_argument(
        "--out-pkl",
        required=True,
        help="a pkl file to write the reconstruction to",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            not Path(x).exists(),  # want to not exist
            FileExistsError(x),
        ),
    )

    # extra "physics" args
    parser.add_argument(
        "--gcdqp-packet-json",
        dest="GCDQp_packet_json",
        required=True,
        help="a JSON file containing the GCDQp_packet (list of I3Frames)",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_file(),
            FileNotFoundError(x),
        ),
    )
    parser.add_argument(
        "--baseline-gcd-file",
        dest="baseline_GCD_file",
        required=True,
        help="the baseline GCD file",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_file(),
            FileNotFoundError(x),
        ),
    )

    args = parser.parse_args()
    logging_tools.set_level(
        cfg.ENV.SKYSCAN_LOG,  # type: ignore[arg-type]
        first_party_loggers="skyscan",
        third_party_level=cfg.ENV.SKYSCAN_LOG_THIRD_PARTY,  # type: ignore[arg-type]
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # get PFrame
    with open(args.in_pkl, "rb") as f:
        msg = pickle.load(f)
        reco_algo = msg[cfg.MSG_KEY_RECO_ALGO]
        pframe = msg[cfg.MSG_KEY_PFRAME]

    # get GCDQp_packet
    with open(args.GCDQp_packet_json, "r") as f:
        GCDQp_packet = full_event_followup.i3live_json_to_frame_packet(
            f.read(), pnf_framing=False
        )

    # go!
    reco_pixel(
        reco_algo,
        pframe,
        GCDQp_packet,
        str(args.baseline_GCD_file),
        args.out_pkl,
    )
    LOGGER.info("Done reco'ing pixel.")


if __name__ == "__main__":
    main()
