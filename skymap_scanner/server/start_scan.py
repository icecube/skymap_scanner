"""The Skymap Scanner Server."""

# pylint: disable=invalid-name,import-error
# fmt:quotes-ok

import argparse
import asyncio
import itertools as it
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import healpy  # type: ignore[import]
import mqclient as mq
import numpy
from I3Tray import I3Units  # type: ignore[import]
from icecube import (  # type: ignore[import]
    astro,
    dataclasses,
    full_event_followup,
    icetray,
)
from rest_tools.client import RestClient
from wipac_dev_tools import argparse_tools, logging_tools

from .. import config as cfg
from .. import recos
from ..utils import extract_json_message, pixelreco
from ..utils.event_tools import EventMetadata
from ..utils.load_scan_state import get_baseline_gcd_frames
from ..utils.utils import pow_of_two
from . import LOGGER
from .choose_new_pixels_to_scan import choose_new_pixels_to_scan
from .reporter import Reporter
from .utils import fetch_event_contents

StrDict = Dict[str, Any]


class DuplicatePixelRecoException(Exception):
    """Raised when a pixel-reco (message) is received that is semantically
    equivalent to a prior.

    For example, a pixel-reco (message) that has the same NSide, Pixel
    ID, and Variation ID as an already received message.
    """


# fmt: off
class PixelsToReco:
    """Manage providing pixels to reco."""

    def __init__(
        self,
        nsides_dict: pixelreco.NSidesDict,
        GCDQp_packet: List[icetray.I3Frame],
        baseline_GCD: str,
        min_nside: int,  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        max_nside: int,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        input_time_name: str,
        input_pos_name: str,
        output_particle_name: str,
        reco_algo: str,
        event_metadata: EventMetadata,
    ) -> None:
        """
        Arguments:
            `nsides_dict`
                - the nsides_dict
            `GCDQp_packet`
                - the GCDQp frame packet
            `min_nside`
                - min nside value
            `max_nside`
                - max nside value
            `input_time_name`
                - name of an I3Double to use as the vertex time for the coarsest scan
            `input_pos_name`
                - name of an I3Position to use as the vertex position for the coarsest scan
            `output_particle_name`
                - name of the output I3Particle
            `reco_algo`
                - name of the reconstruction algorithm to run
            `event_metadata`
                - a collection of metadata about the event
        """
        self.nsides_dict = nsides_dict
        self.input_pos_name = input_pos_name
        self.input_time_name = input_time_name
        self.output_particle_name = output_particle_name
        self.reco_algo = reco_algo.lower()

        # Get Position Variations
        variation_distance = 20.*I3Units.m
        if self.reco_algo == 'millipede_original':
            if cfg.ENV.SKYSCAN_MINI_TEST:
                self.pos_variations = [
                    dataclasses.I3Position(0.,0.,0.),
                    dataclasses.I3Position(-variation_distance,0.,0.)
                ]
            else:
                self.pos_variations = [
                    dataclasses.I3Position(0.,0.,0.),
                    dataclasses.I3Position(-variation_distance,0.,0.),
                    dataclasses.I3Position(variation_distance,0.,0.),
                    dataclasses.I3Position(0.,-variation_distance,0.),
                    dataclasses.I3Position(0., variation_distance,0.),
                    dataclasses.I3Position(0.,0.,-variation_distance),
                    dataclasses.I3Position(0.,0., variation_distance)
                ]
        else:
            self.pos_variations = [
                dataclasses.I3Position(0.,0.,0.),
            ]

        # Set nside values
        if max_nside < min_nside:
            raise ValueError(f"Invalid max/min nside: {max_nside=} < {min_nside=}")
        self.min_nside = min_nside  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        self.max_nside = max_nside  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)

        # Validate & read GCDQp_packet
        p_frame = GCDQp_packet[-1]
        g_frame = get_baseline_gcd_frames(baseline_GCD, GCDQp_packet)[0]

        if p_frame.Stop != icetray.I3Frame.Stream('p'):
            raise RuntimeError("Last frame of the GCDQp packet is not type 'p'.")

        self.fallback_position = p_frame[self.input_pos_name]
        self.fallback_time = p_frame[self.input_time_name].value
        self.fallback_energy = numpy.nan

        self.event_header = p_frame["I3EventHeader"]
        self.event_metadata = event_metadata
        if self.event_metadata.run_id != self.event_header.run_id or self.event_metadata.event_id != self.event_header.event_id:
            raise Exception(
                f"Run/Event Mismatch: {self.event_metadata} vs "
                f"({self.event_header.run_id=}, {self.event_header.event_id=})"
            )

        self.pulseseries_hlc = dataclasses.I3RecoPulseSeriesMap.from_frame(p_frame,'SplitUncleanedInIcePulsesHLC')
        self.omgeo = g_frame["I3Geometry"].omgeo

    @staticmethod
    def refine_vertex_time(vertex, time, direction, pulses, omgeo):
        thc = dataclasses.I3Constants.theta_cherenkov
        ccc = dataclasses.I3Constants.c
        min_d = numpy.inf
        min_t = time
        adj_d = 0
        for om in pulses.keys():
            rvec = omgeo[om].position-vertex
            _l = -rvec*direction
            _d = numpy.sqrt(rvec.mag2-_l**2) # closest approach distance
            if _d < min_d: # closest om
                min_d = _d
                min_t = pulses[om][0].time
                adj_d = _l+_d/numpy.tan(thc)-_d/(numpy.cos(thc)*numpy.sin(thc)) # translation distance
        if numpy.isinf(min_d):
            return time
        return min_t + adj_d/ccc

    def generate_pframes(self) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be reco'd."""

        # find pixels to refine
        pixels_to_refine = choose_new_pixels_to_scan(
            # TODO: replace with self.nsides & implement
            self.nsides_dict, min_nside=self.min_nside, max_nside=self.max_nside
        )
        if len(pixels_to_refine) == 0:
            LOGGER.info("There are no pixels to refine.")
            return
        LOGGER.debug(f"Got pixels to refine: {pixels_to_refine}")

        # sanity check nsides_dict
        for nside in self.nsides_dict:
            for pixel in self.nsides_dict[nside]:
                if (nside,pixel) in pixels_to_refine:
                    raise RuntimeError("pixel to refine is already done processing")

        # submit the pixels we need to submit
        for i, (nside, pix) in enumerate(pixels_to_refine):
            LOGGER.debug(
                f"Generating position-variations from pixel P#{i}: {(nside, pix)}"
            )
            yield from self._gen_pixel_variations(nside=nside, pixel=pix)

    def i3particle(self, position, direction, energy, time):
        # generate the particle from scratch
        particle = dataclasses.I3Particle()
        particle.shape = dataclasses.I3Particle.ParticleShape.InfiniteTrack
        particle.fit_status = dataclasses.I3Particle.FitStatus.OK
        particle.pos = position
        particle.dir = direction
        if self.reco_algo == 'millipede_original':
            LOGGER.debug(f"Reco_algo is {self.reco_algo}, not refining time")
            particle.time = time
        else:
            LOGGER.debug(f"Reco_algo is {self.reco_algo}, refining time")
            # given direction and vertex position, calculate time from CAD
            particle.time = self.refine_vertex_time(
                position,
                time,
                direction,
                self.pulseseries_hlc,
                self.omgeo)
        particle.energy = energy
        return particle

    def _gen_pixel_variations(
        self,
        nside: icetray.I3Int,
        pixel: icetray.I3Int,
    ) -> Iterator[icetray.I3Frame]:
        """Yield PFrames to be reco'd for a given `nside` and `pixel`."""

        dec, ra = healpy.pix2ang(nside, pixel)
        dec = dec - numpy.pi/2.
        zenith, azimuth = astro.equa_to_dir(ra, dec, self.event_metadata.mjd)
        zenith = float(zenith)
        azimuth = float(azimuth)
        direction = dataclasses.I3Direction(zenith,azimuth)

        if nside == self.min_nside:
            position = self.fallback_position
            time = self.fallback_time
            energy = self.fallback_energy
        else:
            coarser_nside = nside
            while True:
                coarser_nside = coarser_nside/2
                coarser_pixel = healpy.ang2pix(int(coarser_nside), dec+numpy.pi/2., ra)

                if coarser_nside < self.min_nside:
                    break # no coarser pixel is available (probably we are just scanning finely around MC truth)
                    #raise RuntimeError("internal error. cannot find an original coarser pixel for nside={0}/pixel={1}".format(nside, pixel))

                if coarser_nside in self.nsides_dict:
                    if coarser_pixel in self.nsides_dict[coarser_nside]:
                        # coarser pixel found
                        break

            if coarser_nside < self.min_nside:
                # no coarser pixel is available (probably we are just scanning finely around MC truth)
                position = self.fallback_position
                time = self.fallback_time
                energy = self.fallback_energy
            else:
                if numpy.isnan(self.nsides_dict[coarser_nside][coarser_pixel].llh):
                    # coarser reconstruction failed
                    position = self.fallback_position
                    time = self.fallback_time
                    energy = self.fallback_energy
                else:
                    position = self.nsides_dict[coarser_nside][coarser_pixel].position
                    time = self.nsides_dict[coarser_nside][coarser_pixel].time
                    energy = self.nsides_dict[coarser_nside][coarser_pixel].energy

        for i in range(0,len(self.pos_variations)):
            p_frame = icetray.I3Frame(icetray.I3Frame.Physics)
            posVariation = self.pos_variations[i]

            if self.reco_algo == 'millipede_wilks':
                # rotate variation to be applied in transverse plane
                posVariation.rotate_y(direction.theta)
                posVariation.rotate_z(direction.phi)
                if position != self.fallback_position:
                    # add fallback pos as an extra first guess
                    p_frame[f'{self.output_particle_name}_fallback'] = self.i3particle(
                        self.fallback_position+posVariation,
                        direction,
                        self.fallback_energy,
                        self.fallback_time)

            p_frame[f'{self.output_particle_name}'] = self.i3particle(position+posVariation,
                                                                      direction,
                                                                      energy,
                                                                      time)
            # generate a new event header
            eventHeader = dataclasses.I3EventHeader(self.event_header)
            eventHeader.sub_event_stream = "SCAN_nside%04u_pixel%04u_posvar%04u" % (nside, pixel, i)
            eventHeader.sub_event_id = int(pixel)
            p_frame["I3EventHeader"] = eventHeader
            p_frame[cfg.I3FRAME_PIXEL] = icetray.I3Int(int(pixel))
            p_frame[cfg.I3FRAME_NSIDE] = icetray.I3Int(int(nside))
            p_frame[cfg.I3FRAME_POSVAR] = icetray.I3Int(int(i))

            LOGGER.debug(
                f"Yielding PFrame (pixel position-variation) PV#{i} "
                f"({pixelreco.pixel_to_tuple(p_frame)}) ({posVariation=})..."
            )
            yield p_frame


# fmt: on
class BestPixelRecoFinder:
    """Facilitate finding the best reco result for any pixel."""

    def __init__(
        self,
        n_posvar: int,  # Number of position variations to collect
    ) -> None:
        if n_posvar <= 0:
            raise ValueError(f"n_posvar is not positive: {n_posvar}")
        self.n_posvar = n_posvar

        self.pixelNumToFramesMap: Dict[
            Tuple[icetray.I3Int, icetray.I3Int], List[pixelreco.PixelReco]
        ] = {}

    def cache_and_get_best(
        self, pixreco: pixelreco.PixelReco
    ) -> Optional[pixelreco.PixelReco]:
        """Add pixreco to internal cache and possibly return the best reco for
        pixel.

        If all the recos for the embedded pixel have be received, return
        the best one. Otherwise, return None.
        """
        index = (pixreco.nside, pixreco.pixel)

        if index not in self.pixelNumToFramesMap:
            self.pixelNumToFramesMap[index] = []
        self.pixelNumToFramesMap[index].append(pixreco)

        if len(self.pixelNumToFramesMap[index]) >= self.n_posvar:
            # find minimum llh
            best = None
            for this in self.pixelNumToFramesMap[index]:
                if (not best) or (this.llh < best.llh and not numpy.isnan(this.llh)):
                    best = this
            if best is None:
                # just push the first if all of them are nan
                best = self.pixelNumToFramesMap[index][0]

            del self.pixelNumToFramesMap[index]  # del list
            return best

        return None

    def finish(self) -> None:
        """Check if all the pixel-recos were received.

        If an entire pixel (and all its pixel-recos) was dropped by
        client(s), this will not catch it.
        """
        if len(self.pixelNumToFramesMap) != 0:
            raise RuntimeError(
                f"Pixels left in cache, not all of the packets seem to be complete: "
                f"{self.pixelNumToFramesMap}"
            )


class PixelRecoCollector:
    """Manage the collecting, filtering, reporting, and saving of pixel-reco
    results."""

    def __init__(
        self,
        n_posvar: int,  # Number of position variations to collect
        nsides_dict: pixelreco.NSidesDict,
        reporter: Reporter,
        pixreco_ids_sent: Set[Tuple[int, int, int]],
    ) -> None:
        self._finder = BestPixelRecoFinder(n_posvar=n_posvar)
        self.reporter = reporter
        self.nsides_dict = nsides_dict
        self.pixreco_ids_received: Set[Tuple[int, int, int]] = set([])
        self.pixreco_ids_sent = pixreco_ids_sent

    async def __aenter__(self) -> "PixelRecoCollector":
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self._finder.finish()

    async def collect(
        self,
        pixreco: pixelreco.PixelReco,
        pixreco_start: float,
        pixreco_end: float,
    ) -> None:
        """Cache pixreco until we can save the pixel's best received reco."""
        LOGGER.debug(f"{self.nsides_dict=}")

        if pixreco.id_tuple in self.pixreco_ids_received:
            raise DuplicatePixelRecoException(
                f"Pixel-reco has already been received: {pixreco.id_tuple}"
            )
        if pixreco.id_tuple not in self.pixreco_ids_sent:
            raise DuplicatePixelRecoException(
                f"Pixel-reco received not in sent set, it is probably from an earlier iteration: {pixreco.id_tuple}"
            )

        self.pixreco_ids_received.add(pixreco.id_tuple)
        logging_id = f"S#{len(self.pixreco_ids_received) - 1}"
        LOGGER.info(f"Got a pixel-reco {logging_id} {pixreco}")

        # get best pixreco
        best = self._finder.cache_and_get_best(pixreco)
        LOGGER.info(f"Cached pixel-reco {pixreco.id_tuple} {pixreco}")

        # save best pixreco (if we got it)
        if not best:
            LOGGER.debug(f"Best pixel-reco not yet found ({pixreco.id_tuple} {pixreco}")
        else:
            LOGGER.info(
                f"Saving a BEST pixel-reco (found {logging_id}): "
                f"{best.id_tuple} {best}"
            )
            # insert pixreco into nsides_dict
            if best.nside not in self.nsides_dict:
                self.nsides_dict[best.nside] = {}
            if best.pixel in self.nsides_dict[best.nside]:
                raise DuplicatePixelRecoException(
                    f"NSide {best.nside} / Pixel {best.pixel} is already in nsides_dict"
                )
            self.nsides_dict[best.nside][best.pixel] = best
            LOGGER.debug(f"Saved (found during {logging_id}): {best.id_tuple} {best}")

        # report after potential save
        await self.reporter.record_pixreco(pixreco.nside, pixreco_start, pixreco_end)


async def serve(
    scan_id: str,
    reco_algo: str,
    event_metadata: EventMetadata,
    nsides_dict: Optional[pixelreco.NSidesDict],
    GCDQp_packet: List[icetray.I3Frame],
    baseline_GCD: str,
    output_dir: Optional[Path],
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    min_nside: int,  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
    max_nside: int,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
    skydriver_rc: Optional[RestClient],
) -> pixelreco.NSidesDict:
    """Send pixels to be reco'd by client(s), then collect results and save to
    disk."""
    global_start_time = time.time()
    LOGGER.info(f"Starting up Skymap Scanner server for event: {event_metadata=}")

    if not nsides_dict:
        nsides_dict = {}

    pixeler = PixelsToReco(
        nsides_dict=nsides_dict,
        GCDQp_packet=GCDQp_packet,
        baseline_GCD=baseline_GCD,
        min_nside=min_nside,  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        max_nside=max_nside,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        input_time_name=cfg.INPUT_TIME_NAME,
        input_pos_name=cfg.INPUT_POS_NAME,
        output_particle_name=cfg.OUTPUT_PARTICLE_NAME,
        reco_algo=reco_algo,
        event_metadata=event_metadata,
    )

    reporter = Reporter(
        scan_id,
        global_start_time,
        nsides_dict,
        len(pixeler.pos_variations),
        min_nside,  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        max_nside,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        skydriver_rc,
        event_metadata,
    )
    await reporter.precomputing_report()

    # Start the scan iteration loop
    total_n_pixreco = 0
    for i in it.count():
        logging.info(f"Starting new scan iteration (#{i})")
        n_pixreco = await serve_scan_iteration(
            to_clients_queue,
            from_clients_queue,
            reco_algo,
            nsides_dict,
            pixeler,
            reporter,
        )
        if not n_pixreco:  # we're done
            break
        total_n_pixreco += n_pixreco

    # sanity check
    if not total_n_pixreco:
        raise RuntimeError("No pixels were ever sent.")

    # get, log, & post final results
    # TODO: remove 'total_n_pixreco' for https://github.com/icecube/skymap_scanner/issues/84
    result = await reporter.after_computing_report(total_n_pixreco)

    # write out .npz & .json files
    if output_dir:
        npz_fpath = result.to_npz(event_metadata, output_dir)
        json_fpath = result.to_json(event_metadata, output_dir)
        LOGGER.info(f"Output Files: {npz_fpath}, {json_fpath}")

    return nsides_dict


async def serve_scan_iteration(
    to_clients_queue: mq.Queue,
    from_clients_queue: mq.Queue,
    reco_algo: str,
    nsides_dict: pixelreco.NSidesDict,
    pixeler: PixelsToReco,
    reporter: Reporter,
) -> int:
    """Run the next (or first) scan iteration (set of pixel-recos).

    Return the number of pixels sent. Stop when this is 0.
    """

    #
    # SEND PIXELS
    #

    # get pixels & send to client(s)
    LOGGER.info("Getting pixels to send to clients...")
    pixreco_ids_sent = set([])
    async with to_clients_queue.open_pub() as pub:
        for i, pframe in enumerate(pixeler.generate_pframes()):  # queue_to_clients
            _tup = pixelreco.pixel_to_tuple(pframe)
            LOGGER.info(f"Sending message M#{i} ({_tup})...")
            await pub.send(
                {
                    cfg.MSG_KEY_RECO_ALGO: reco_algo,
                    cfg.MSG_KEY_PFRAME: pframe,
                }
            )
            pixreco_ids_sent.add(_tup)

    # check if anything was actually processed
    if not pixreco_ids_sent:
        LOGGER.info("No pixels were sent for this iteration.")
        return 0
    LOGGER.info(f"Done serving pixel-variations to clients: {len(pixreco_ids_sent)}.")

    #
    # COLLECT PIXEL-RECOS
    #

    collector = PixelRecoCollector(
        n_posvar=len(pixeler.pos_variations),
        nsides_dict=nsides_dict,
        reporter=reporter,
        pixreco_ids_sent=pixreco_ids_sent,
    )

    # get pixel-recos from client(s), collect and save
    LOGGER.info("Receiving pixel-recos from clients...")
    async with collector as col:  # enter collector 1st for detecting when no pixel-recos received
        async with from_clients_queue.open_sub() as sub:
            async for msg in sub:
                if not isinstance(msg['pixreco'], pixelreco.PixelReco):
                    raise ValueError(
                        f"Message not {pixelreco.PixelReco}: {type(msg['pixreco'])}"
                    )
                try:
                    await col.collect(msg['pixreco'], msg['start'], msg['end'])
                except DuplicatePixelRecoException as e:
                    logging.error(e)
                # if we've got all the pixrecos, no need to wait for queue's timeout
                if col.pixreco_ids_sent == col.pixreco_ids_received:
                    break

    LOGGER.info("Done receiving/saving pixel-recos from clients.")
    return len(pixreco_ids_sent)


def write_startup_json(
    client_startup_json: Path,
    event_metadata: EventMetadata,
    min_nside: int,  # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
    max_nside: int,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
    baseline_GCD_file: str,
    GCDQp_packet: List[icetray.I3Frame],
) -> str:
    """Write startup JSON file for client-spawning.

    Return the scan_id string.
    """
    if cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID:
        scan_id = cfg.ENV.SKYSCAN_SKYDRIVER_SCAN_ID
    else:
        # TODO: replace with nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        # scan_id = f"{event_id}-{'-'.join(f'{n}:{x}' for n,x in nsides)}-{int(time.time())}"
        scan_id = f"{str(event_metadata)}-{min_nside}-{max_nside}-{int(time.time())}"

    json_dict = {
        "scan_id": scan_id,
        "mq_basename": scan_id,
        "baseline_GCD_file": baseline_GCD_file,
        "GCDQp_packet": json.loads(
            full_event_followup.frame_packet_to_i3live_json(
                GCDQp_packet, pnf_framing=False
            )
        ),
    }

    with open(client_startup_json, "w") as f:
        json.dump(json_dict, f)
    LOGGER.info(
        f"Startup JSON: {client_startup_json} ({client_startup_json.stat().st_size} bytes)"
    )

    return json_dict["scan_id"]  # type: ignore[no-any-return]


def main() -> None:
    """Get command-line arguments and perform event scan via clients."""

    def _nside_and_pixelextension(val: str) -> int:  # -> Tuple[int, int]:
        val = val.split(":")[0]  # for SkyDriver until real implementation (below)
        return pow_of_two(val)
        # TODO: use code below instead (https://github.com/icecube/skymap_scanner/issues/79)
        # nside, ext = val.split(":")
        # return pow_of_two(nside), int(ext)

    parser = argparse.ArgumentParser(
        description=(
            "Start up server to serve pixels to clients and save pixel-reconstructions "
            "from clients for a given event."
        ),
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # directory args
    parser.add_argument(
        "--client-startup-json",
        required=True,
        help="The filepath to save the JSON needed to spawn clients (the parent directory must already exist)",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).parent.is_dir(),
            NotADirectoryError(Path(x).parent),
        ),
    )
    parser.add_argument(
        "-c",
        "--cache-dir",
        required=True,
        help="The cache directory to use",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_dir(),
            NotADirectoryError(x),
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="The directory to write out the .npz file",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).is_dir(),
            NotADirectoryError(x),
        ),
    )

    # "physics" args
    parser.add_argument(
        "--reco-algo",
        choices=recos.get_all_reco_algos(),
        help="The reconstruction algorithm to use",
    )
    parser.add_argument(
        "-e",
        "--event-file",
        default=None,
        help="The file containing the event to scan (.pkl or .json)",
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            (x.endswith(".pkl") or x.endswith(".json")) and Path(x).is_file(),
            argparse.ArgumentTypeError(
                f"Invalid Event: '{x}' Event needs to be a .pkl or .json file."
            ),
        ),
    )
    parser.add_argument(
        "-g",
        "--gcd-dir",
        default=cfg.DEFAULT_GCD_DIR,
        help="The GCD directory to use",
        type=Path,
    )
    parser.add_argument(
        "--nsides",
        default=[
            cfg.MIN_NSIDE_DEFAULT,
            cfg.MAX_NSIDE_DEFAULT,
        ],  # TODO: [(8,12), (64,12), (512,24)] (https://github.com/icecube/skymap_scanner/issues/79)
        help=(
            "The min and max nside value, if one value is given only do that one iteration"
            # TODO: use message below instead (https://github.com/icecube/skymap_scanner/issues/79)
            # "The nside values to use for each iteration, "
            # "each ':'-paired with their pixel extension value. "
            # "Example: --nsides 8:12 64:12 512:24"
        ),
        nargs='*',
        type=_nside_and_pixelextension,
    )
    # --real-event XOR --simulated-event
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--real-event",
        action="store_true",
        help='include this flag if the event is real',
    )
    group.add_argument(
        "--simulated-event",
        action="store_true",
        help='include this flag if the event was simulated',
    )

    args = parser.parse_args()
    logging_tools.set_level(
        cfg.ENV.SKYSCAN_LOG,
        first_party_loggers="skyscan",
        third_party_level=cfg.ENV.SKYSCAN_LOG_THIRD_PARTY,
        use_coloredlogs=True,
        future_third_parties=["google", "pika"],  # at most only one will be used
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # nsides
    args.nsides = sorted(args.nsides)
    # TODO: un-comment validity check below (https://github.com/icecube/skymap_scanner/issues/79)
    # if list(set(n[0] for n in args.nsides)) != [n[0] for n in args.nsides]:
    #     raise argparse.ArgumentTypeError(
    #         f"'--nsides' cannot contain duplicate nsides: {args.nsides}"
    #     )
    # TODO - actually implement variable nside sequences (https://github.com/icecube/skymap_scanner/issues/79)
    # for now...
    if len(args.nsides) > 2:
        raise argparse.ArgumentTypeError("'--nsides' cannot contain more than 2 values")
    min_nside = args.nsides[0]
    max_nside = args.nsides[-1]  # if only one value, then also grab index-0
    logging.warning(
        f"VARIABLE NSIDE SEQUENCES NOT YET IMPLEMENTED: using {min_nside=} & {max_nside=} with default pixel-extension values"
    )

    # check if Baseline GCD directory is reachable (also checks default value)
    if not Path(args.gcd_dir).is_dir():
        raise NotADirectoryError(args.gcd_dir)

    # make skydriver REST connection
    if cfg.ENV.SKYSCAN_SKYDRIVER_ADDRESS:
        skydriver_rc = RestClient(
            cfg.ENV.SKYSCAN_SKYDRIVER_ADDRESS, token=cfg.ENV.SKYSCAN_SKYDRIVER_AUTH
        )
    else:
        skydriver_rc = None
        if not args.output_dir:
            raise RuntimeError(
                "Must include either --output-dir or SKYSCAN_SKYDRIVER_ADDRESS (env var), "
                f"otherwise you won't see your results!"
            )

    # read event file
    event_contents = fetch_event_contents(args.event_file, skydriver_rc)

    # get inputs (load event_id + state_dict cache)
    event_metadata, state_dict = extract_json_message.extract_json_message(
        event_contents,
        reco_algo=args.reco_algo,
        is_real_event=args.real_event,
        cache_dir=str(args.cache_dir),
        GCD_dir=str(args.gcd_dir),
    )

    # write startup files for client-spawning
    scan_id = write_startup_json(
        args.client_startup_json,
        event_metadata,
        min_nside,  # TODO: replace with args.nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
        max_nside,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
        state_dict[cfg.STATEDICT_BASELINE_GCD_FILE],
        state_dict[cfg.STATEDICT_GCDQP_PACKET],
    )

    # make mq connections
    LOGGER.info("Making MQClient queue connections...")
    to_clients_queue = mq.Queue(
        cfg.ENV.SKYSCAN_BROKER_CLIENT,
        address=cfg.ENV.SKYSCAN_BROKER_ADDRESS,
        name=f"to-clients-{scan_id}",
        auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
        timeout=cfg.ENV.SKYSCAN_MQ_TIMEOUT_TO_CLIENTS,
    )
    from_clients_queue = mq.Queue(
        cfg.ENV.SKYSCAN_BROKER_CLIENT,
        address=cfg.ENV.SKYSCAN_BROKER_ADDRESS,
        name=f"from-clients-{scan_id}",
        auth_token=cfg.ENV.SKYSCAN_BROKER_AUTH,
        timeout=cfg.ENV.SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS,
    )

    # go!
    asyncio.run(
        serve(
            scan_id=scan_id,
            reco_algo=args.reco_algo,
            event_metadata=event_metadata,
            nsides_dict=state_dict.get(cfg.STATEDICT_NSIDES),
            GCDQp_packet=state_dict[cfg.STATEDICT_GCDQP_PACKET],
            baseline_GCD=state_dict[cfg.STATEDICT_BASELINE_GCD_FILE],
            output_dir=args.output_dir,
            to_clients_queue=to_clients_queue,
            from_clients_queue=from_clients_queue,
            min_nside=min_nside,  # TODO: replace with args.nsides & implement (https://github.com/icecube/skymap_scanner/issues/79)
            max_nside=max_nside,  # TODO: remove (https://github.com/icecube/skymap_scanner/issues/79)
            skydriver_rc=skydriver_rc,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
