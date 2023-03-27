"""Tools for picking pixels to scan."""

# fmt: off
# pylint: skip-file

import random
from typing import List, Optional, Tuple

import healpy  # type: ignore[import]
import numpy
from icecube import icetray  # type: ignore[import]

from ..config import NSideProgression
from ..utils.pixelreco import NSidesDict
from . import LOGGER
from .utils import validate_nside_progression


def __healpix_pixel_upgrade(nside, pix) -> list:
    pix_nested = healpy.ring2nest(nside, pix)
    pix_upgraded = (pix_nested << 2)
    sub_pixels = [pix_upgraded, pix_upgraded+1, pix_upgraded+2, pix_upgraded+3]
    return healpy.nest2ring(nside*2, sub_pixels)


def healpix_pixel_upgrade(from_nside, to_nside, pix) -> list:
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
def find_pixels_around_pixel(request_nside, pix_nside, pix, num=10) -> list:
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
    global_min_pix_index: Tuple[Optional[int], Optional[int]] = (None, None)
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
    pixel_extension_number: int,
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
    global_min_pix_nside, global_min_pix_index = find_global_min_pixel(nsides_dict)
    if global_min_pix_index is not None:
        all_refine_pixels = find_pixels_around_pixel(nside, global_min_pix_nside, global_min_pix_index, num=pixel_extension_number)
        pixels_to_refine.update([x for x in all_refine_pixels if x in pixels_dict])

    return [x for x in pixels_to_refine]


def choose_new_pixels_to_scan_around_MCtruth(
    nsides_dict: NSidesDict,
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
        existing_pixels: List[int] = []
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
    nsides_dict: NSidesDict,
    nside_progression: NSideProgression,
    ang_dist: float = 2.,
    mc_ra_dec: Optional[Tuple[float, float]] = None,
) -> List[Tuple[icetray.I3Int, icetray.I3Int]]:
    """Get the next set of pixels to scan/refine by searching `nsides_dict`."""
    nside_progression = validate_nside_progression(nside_progression)

    # special case if we have MC truth
    if mc_ra_dec:
        LOGGER.debug("Getting pixels around MC truth...")
        # scan only at max_nside around the true minimum
        return choose_new_pixels_to_scan_around_MCtruth(
            nsides_dict,
            mc_ra_dec=mc_ra_dec,
            nside=nside_progression[-1][0],  # use final nside
            angular_dist=ang_dist*numpy.pi/180.
        )

    # initial pixel generation
    if not nsides_dict:
        LOGGER.debug(f"No previous nsides_dict, getting pixels for {nside_progression[0][0]}...")
        scan_pixels = list(range(healpy.nside2npix(nside_progression[0][0])))
        random.shuffle(scan_pixels)
        return [(nside_progression[0][0], pix) for pix in scan_pixels]

    # generate pixels to refine
    all_pixels_to_refine: List[Tuple[icetray.I3Int, icetray.I3Int]] = []
    # iterate through each nside looking for what subset of pixels to reco using the next nside
    for i, (current_nside, pixel_extension_number) in enumerate(nside_progression[:-1]):  # skip final
        next_nside = nside_progression[i+1][0]  # index will always be defined since we're not iterating the final nside
        LOGGER.debug(
            f"Attempting to get pixels for ("
            f"current_nside={current_nside}, "
            f"pixel_extension_number={pixel_extension_number}, "
            f"next_nside={next_nside})..."
        )

        # Find which (finished) pixels are best to refine
        pixels_to_refine = find_pixels_to_refine(
            nsides_dict,
            nside=current_nside,
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
            # (filter out those previously generated)
            if next_nside in nsides_dict:
                upgraded_pixels_to_refine = [
                    pix for pix in upgraded_pixels_to_refine
                    if pix not in nsides_dict[next_nside].keys()
                ]
            LOGGER.debug(f"Extending list of pixels (nside={next_nside}) by {len(upgraded_pixels_to_refine)} ({upgraded_pixels_to_refine})...")
            all_pixels_to_refine.extend([(next_nside, pix) for pix in upgraded_pixels_to_refine])

    LOGGER.debug(f"Search Complete: Got {len(all_pixels_to_refine)} pixels to refine: {all_pixels_to_refine}.")
    return all_pixels_to_refine
