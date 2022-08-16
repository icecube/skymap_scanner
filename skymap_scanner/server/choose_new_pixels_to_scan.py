"""Tools for picking pixels to scan."""

# fmt: off
# pylint: skip-file

import random
from typing import List, Optional, Tuple

import healpy  # type: ignore[import]
import numpy
from icecube import icetray  # type: ignore[import]

from .. import config as cfg
from ..utils.load_scan_state import load_cache_state
from ..utils.pixelreco import NSidesDict
from . import LOGGER


def __healpix_pixel_upgrade(nside, pix):
    pix_nested = healpy.ring2nest(nside, pix)
    pix_upgraded = (pix_nested << 2)
    sub_pixels = [pix_upgraded, pix_upgraded+1, pix_upgraded+2, pix_upgraded+3]
    return healpy.nest2ring(nside*2, sub_pixels)


def healpix_pixel_upgrade(from_nside, to_nside, pix):
    if to_nside < from_nside:
        raise RuntimeError("to_nside needs to be greater than from_nside")
    if to_nside==from_nside:
        return [pix]

    current_nside = from_nside
    pixels = [pix]

    while True:
        new_pixels = []
        for p in pixels:
            new_pixels.extend( __healpix_pixel_upgrade(current_nside, p) )

        pixels = new_pixels
        current_nside = current_nside*2
        if current_nside==to_nside:
            return pixels
        if current_nside > to_nside:
            raise RuntimeError("invalid to_nside")


# TODO: maybe use healpy to find neighboring pixels and scan all 8 neighbors+the current pixel
def find_pixels_around_pixel(request_nside, pix_nside, pix, num=10):
    pixel_area = healpy.nside2pixarea(request_nside)
    area_for_requested_pixels = pixel_area*float(num)
    radius_around = numpy.sqrt(area_for_requested_pixels/numpy.pi)

    x0,y0,z0 = healpy.pix2vec(pix_nside, pix)

    x1,y1,z1 = healpy.pix2vec(request_nside, numpy.asarray(list(range(healpy.nside2npix(request_nside)))))
    cos_space_angle = numpy.clip(x0*x1 + y0*y1 + z0*z1, -1., 1.)
    space_angle = numpy.arccos(cos_space_angle)
    pixels = numpy.where(space_angle < radius_around)[0]
    pixel_space_angles = space_angle[pixels]
    # pixels, sorted by distance from the requested pixel
    return pixels[numpy.argsort(pixel_space_angles)].tolist()


def pixel_dist(from_nside, from_pix, to_nside, to_pix):
    x0,y0,z0 = healpy.pix2vec(from_nside, from_pix)
    x1,y1,z1 = healpy.pix2vec(to_nside, to_pix)
    cos_space_angle = numpy.clip(x0*x1 + y0*y1 + z0*z1, -1., 1.)
    space_angle = numpy.arccos(cos_space_angle)
    return space_angle


def find_global_min_pixel(nsides_dict: NSidesDict) -> Tuple[Optional[int], Optional[int]]:
    global_min_pix_index = (None, None)
    min_llh = None

    for nside in list(nsides_dict.keys()):
        pixels_dict = nsides_dict[nside]
        for p in list(pixels_dict.keys()):
            this_llh = pixels_dict[p].llh
            if min_llh is None or ((not numpy.isnan(this_llh)) and (this_llh < min_llh)):
                global_min_pix_index=(nside,p)
                min_llh=this_llh

    return global_min_pix_index


def find_pixels_to_refine(
    nsides_dict: NSidesDict,
    nside: int,
    total_pixels_for_this_nside: int,
    pixel_extension_number: int = 24,
    llh_diff_to_trigger_refinement: int = 200000,
) -> List[int]:
    if nside not in nsides_dict:
        return []

    pixels_dict = nsides_dict[nside]

    pixels_to_refine = set()

    # refine pixels that have neighbors with a high likelihood ratio
    for pixel in list(pixels_dict.keys()):
        pixel_llh = pixels_dict[pixel].llh
        if numpy.isnan(pixel_llh): continue # do not refine nan pixels
        neighbors = healpy.get_all_neighbours(nside, pixel)

        for neighbor in neighbors:
            if neighbor==-1: continue
            if neighbor not in pixels_dict: continue
            neighbor_llh = pixels_dict[neighbor].llh

            llh_diff = 2.*numpy.abs(pixel_llh-neighbor_llh) # Wilk's theorem
            if llh_diff > llh_diff_to_trigger_refinement:
                # difference greater than the llh threshold,
                # add the pixel and its neighbor
                pixels_to_refine.add(pixel)
                pixels_to_refine.add(neighbor)

    # refine the global minimum

    num_pixels = len(pixels_dict)
    max_pixels = total_pixels_for_this_nside
    # print("nside", nside, "total_pixels_for_this_nside", max_pixels, "num_pixels", num_pixels)
    if float(num_pixels)/float(max_pixels) > 0.3: # start only once 30% have been scanned
        global_min_pix_nside, global_min_pix_index = find_global_min_pixel(state_dict)

        if global_min_pix_index is not None:
            all_refine_pixels = find_pixels_around_pixel(nside, global_min_pix_nside, global_min_pix_index, num=pixel_extension_number)
            pixels_to_refine.update([x for x in all_refine_pixels if x in pixels_dict])

    return [x for x in pixels_to_refine]


def choose_new_pixels_to_scan_around_MCtruth(
    nsides_dict: Optional[NSidesDict],
    mc_ra_dec: Tuple[float, float],
    nside: int,
    angular_dist: float = 2.*numpy.pi/180.,
) -> List[Tuple[icetray.I3Int, icetray.I3Int]]:
    ra, dec = mc_ra_dec

    # MC true pixel
    true_pix = healpy.ang2pix(nside, dec+numpy.pi/2., ra)

    # true pixel dir
    x0,y0,z0 = healpy.pix2vec(nside, true_pix)

    # all possible pixels
    x1,y1,z1 = healpy.pix2vec(nside, numpy.asarray(list(range(healpy.nside2npix(nside)))))

    cos_space_angle = numpy.clip(x0*x1 + y0*y1 + z0*z1, -1., 1.)
    space_angle = numpy.arccos(cos_space_angle)
    pixels = numpy.where(space_angle < angular_dist)[0]
    pixel_space_angles = space_angle[pixels]

    # pixels, sorted by distance from the requested pixel
    sorted_pixels = pixels[numpy.argsort(pixel_space_angles)].tolist()

    if not nsides_dict:
        existing_pixels = []
    else:
        if nside not in nsides_dict:
            existing_pixels = []
        else:
            existing_pixels = list(nsides_dict[nside].keys())

    scan_pixels = []

    for p in sorted_pixels:
        if p not in existing_pixels:
            scan_pixels.append( (nside, p) )

    #scan_pixels = [(nside, pix) for pix in sorted_pixels]

    return scan_pixels


def choose_new_pixels_to_scan(
    nsides_dict: Optional[NSidesDict],
    max_nside: int = cfg.MAX_NSIDE_DEFAULT,
    ang_dist: float = 2.,
    min_nside: int = cfg.MIN_NSIDE_DEFAULT,
    mc_ra_dec: Optional[Tuple[float, float]] = None,
) -> List[Tuple[icetray.I3Int, icetray.I3Int]]:
    """Get the next set of pixels to scan/refine by searching the nsides_dict."""

    # special case if we have MC truth
    if mc_ra_dec:
        LOGGER.debug("Getting pixels around MC truth...")
        # scan only at max_nside around the true minimum
        return choose_new_pixels_to_scan_around_MCtruth(
            nsides_dict,
            mc_ra_dec=mc_ra_dec,
            nside=max_nside,
            angular_dist=ang_dist*numpy.pi/180.
        )

    # first check if any pixels with nside=min_nside are missing (we need all of them)
    if not nsides_dict:
        LOGGER.debug(f"No previous nsides_dict, getting pixels for min_nside={min_nside}...")
        # print("nsides is missing - scan all pixels at nside=min_nside")
        scan_pixels = list(range(healpy.nside2npix(min_nside)))
        random.shuffle(scan_pixels)
        return [(min_nside, pix) for pix in scan_pixels]
    if min_nside not in nsides_dict:
        LOGGER.debug(f"Missing min_nside in previous nsides_dict, getting pixels for min_nside={min_nside}...")
        # print("nsides=min_nside is missing - scan all pixels at nside=min_nside")
        scan_pixels = list(range(healpy.nside2npix(min_nside)))
        random.shuffle(scan_pixels)
        return [(min_nside, pix) for pix in scan_pixels]

    # Find any unfinished pixels for min_nside (LEGACY CODE)
    scan_pixels = []
    for i in range(healpy.nside2npix(min_nside)):
        if i not in nsides_dict[min_nside].keys():
            scan_pixels.append(i)
    if len(scan_pixels) > 0:
        random.shuffle(scan_pixels)
        all_pixels_to_refine = [(min_nside, pix) for pix in scan_pixels]
        LOGGER.debug(
            f"Found {len(all_pixels_to_refine)} unfinished pixels for min_nside={min_nside} ({all_pixels_to_refine})..."
        )
    else:
        all_pixels_to_refine = []

    # some or all 768 pixels with nside min_nside exist
    # start w/ min
    current_nside = min_nside

    # first iteration will upgrade from nside=min_nside to nside=16, next one from 16 to 32, ...
    while True:
        pixel_extension_number = 12
        if current_nside < 64:
            # 8 -> 64, 64 subdivisions per existing pixel
            next_nside = 64
            pixel_extension_number = 12 # scan 12*64=768 pixels
        elif current_nside < max_nside:
            # 64 -> 1024, 256 subdivisons per existing pixel
            next_nside = max_nside
            pixel_extension_number = 24 # scan 12*256=3072 pixels
        else:
            # should not get here, max_nside is 1024
            next_nside = current_nside*8
            pixel_extension_number = 12
        LOGGER.debug(
            f"Attempting to get pixels for ("
            f"current_nside={current_nside}, "
            f"pixel_extension_number={pixel_extension_number}, "
            f"next_nside={next_nside})..."
        )

        if next_nside > max_nside:
            LOGGER.debug(f"No more pixels to scan: (next_nside={next_nside} > max_nside={max_nside})")
            break # no more pixels to scan

        total_pixels_scanning_and_existing = set()
        if current_nside in nsides_dict:
            total_pixels_scanning_and_existing.update(list(nsides_dict[current_nside].keys()))
        for __n, __p in all_pixels_to_refine:
            if __n == current_nside:
                total_pixels_scanning_and_existing.add(__p)

        pixels_to_refine = find_pixels_to_refine(
            nsides_dict,
            nside=current_nside,
            total_pixels_for_this_nside=len(total_pixels_scanning_and_existing),
            pixel_extension_number=pixel_extension_number
        )
        LOGGER.debug(f"Found {len(pixels_to_refine)} pixels to refine: {pixels_to_refine}...")
        if len(pixels_to_refine) > 0:
            # have the list of pixels to refine - find their subdivisions

            upgraded_pixels_to_refine = []
            for p in pixels_to_refine:
                u = healpix_pixel_upgrade(current_nside, next_nside, p) # upgrade to the next nside
                upgraded_pixels_to_refine.extend(u)

            # only scan non-existent pixels
            if next_nside in nsides_dict:
                upgraded_pixels_to_refine_nonexisting = [
                    pix for pix in upgraded_pixels_to_refine
                    if pix not in nsides_dict[next_nside].keys()
                ]
            else:
                upgraded_pixels_to_refine_nonexisting = upgraded_pixels_to_refine

            to_extend = [(next_nside, pix) for pix in upgraded_pixels_to_refine_nonexisting]
            LOGGER.debug(f"Extending list of pixels by {len(to_extend)} ({to_extend})...")
            all_pixels_to_refine.extend(to_extend)

        current_nside = next_nside # test the next nside

    LOGGER.debug(f"Search Complete: Got {len(all_pixels_to_refine)} pixels to refine: {all_pixels_to_refine}.")
    return all_pixels_to_refine


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    state_dict = load_cache_state(
        eventID,
        cfg.RecoAlgo[args.reco_algo.upper()],  # TODO: add --reco-algo (see start_scan.py)
        cache_dir=options.CACHEDIR
    )[1]
    pixels = choose_new_pixels_to_scan(state_dict[cfg.STATEDICT_NSIDES])

    print(("got", pixels))
    print(("number of pixels to scan is", len(pixels)))
