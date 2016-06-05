import os
import numpy
import healpy
import random

def healpix_pixel_upgrade(nside, pix):
    pix_nested = healpy.ring2nest(nside, pix)
    pix_upgraded = (pix_nested << 2)
    sub_pixels = [pix_upgraded, pix_upgraded+1, pix_upgraded+2, pix_upgraded+3]
    return healpy.nest2ring(nside*2, sub_pixels)

def healpix_pixel_downgrade(nside, pix):
    pix_nested = healpy.ring2nest(nside, pix)
    pix_downgraded = (pix_nested >> 2)
    return healpy.nest2ring(nside/2, pix_downgraded)

def find_pixels_around_pixel(nside, pix, num=100):
    pixel_area = healpy.nside2pixarea(nside)
    pixels_around_minimum=float(num)
    radius_around_sq = pixel_area*pixels_around_minimum/numpy.pi
    
    ret_pixels = []
    
    x0,y0,z0 = healpy.pix2vec(nside, pix)
    for i in range(healpy.nside2npix(nside)):
        x1,y1,z1 = healpy.pix2vec(nside, i)
        cos_space_angle = x0*x1 + y0*y1 + z0*z1
        if cos_space_angle >  1.: cos_space_angle= 1.
        if cos_space_angle < -1.: cos_space_angle=-1.
        space_angle = numpy.arccos(cos_space_angle)    
        
        if space_angle <= radius_around_sq:
            ret_pixels.append(i)
        
    # print "expected pixels=", num, " returned pixels=", len(ret_pixels)
    return ret_pixels
        

def find_pixels_to_refine(state_dict, nside, total_pixels_for_this_nside, llh_diff_to_trigger_refinement=4000):
    if nside not in state_dict["nsides"]:
        return []

    pixels_dict = state_dict["nsides"][nside]

    pixels_to_refine = set()

    # refine pixels that have neighbors with a high likelihood ratio
    for pixel in pixels_dict.keys():
        pixel_llh = pixels_dict[pixel]["llh"]
        if numpy.isnan(pixel_llh): continue # do not refine nan pixels
        neighbors = healpy.get_all_neighbours(nside, pixel)

        for neighbor in neighbors:
            if neighbor==-1: continue
            if neighbor not in pixels_dict: continue
            neighbor_llh = pixels_dict[neighbor]["llh"]

            llh_diff = 2.*numpy.abs(pixel_llh-neighbor_llh) # Wilk's theorem
            if llh_diff > llh_diff_to_trigger_refinement:
                # difference greater than the llh threshold,
                # add the pixel and its neighbor
                pixels_to_refine.add(pixel)
                pixels_to_refine.add(neighbor)

    # refine the global minimum

    num_pixels = len(pixels_dict)
    max_pixels = total_pixels_for_this_nside
    print "nside", nside, "total_pixels_for_this_nside", max_pixels, "num_pixels", num_pixels
    if float(num_pixels)/float(max_pixels) > 0.3: # start only once 30% have been scanned
        global_min_pix_index = None
        min_llh = None
        for p in pixels_dict.keys():
            this_llh = pixels_dict[p]['llh']
            if global_min_pix_index is None or ((not numpy.isnan(this_llh)) and (this_llh < min_llh)):
                global_min_pix_index=p
                min_llh=this_llh
        
        if global_min_pix_index is not None:
            all_refine_pixels = find_pixels_around_pixel(nside, global_min_pix_index, num=100)
            
            pixels_to_refine = [x for x in all_refine_pixels if x in pixels_dict]
    
    return [x for x in pixels_to_refine]

def choose_new_pixels_to_scan(state_dict, max_nside=1024):
    # first check if any pixels with nside=8 are missing (we need all of them)
    if "nsides" not in state_dict:
        print "nsides is missing - scan all pixels at nside=8"
        scan_pixels = range(healpy.nside2npix(8))
        random.shuffle(scan_pixels)
        return [(8, pix) for pix in scan_pixels]
    if 8 not in state_dict["nsides"]:
        print "nsides=8 is missing - scan all pixels at nside=8"
        scan_pixels = range(healpy.nside2npix(8))
        random.shuffle(scan_pixels)
        return [(8, pix) for pix in scan_pixels]

    scan_pixels = []
    existing_pixels = state_dict["nsides"][8].keys()
    for i in range(healpy.nside2npix(8)):
        if i not in existing_pixels:
            scan_pixels.append(i)

    if len(scan_pixels) > 0:
        random.shuffle(scan_pixels)
        scan_pixels = [(8, pix) for pix in scan_pixels]

    # some or all 768 pixels with nside 8 exist
    current_nside = 8

    all_pixels_to_refine = scan_pixels

    # first iteration will upgrade from nside=8 to nside=16, next one from 16 to 32, ...
    while True:
        if current_nside*2 > max_nside:
            break # no more pixels to scan

        total_pixels_scanning_and_existing = set()
        if current_nside in state_dict["nsides"]:
            total_pixels_scanning_and_existing.update(state_dict["nsides"][current_nside].keys())
        for __n, __p in all_pixels_to_refine:
            if __n == current_nside: total_pixels_scanning_and_existing.add(__p)
        total_pixels_scanning_and_existing = len(total_pixels_scanning_and_existing)

        pixels_to_refine = find_pixels_to_refine(state_dict, nside=current_nside, total_pixels_for_this_nside=total_pixels_scanning_and_existing)
        if len(pixels_to_refine) > 0:
            random.shuffle(pixels_to_refine)
            # have the list of pixels to refine - find their subdivisions

            upgraded_pixels_to_refine = []
            for p in pixels_to_refine:
                u = healpix_pixel_upgrade(current_nside, p) # upgrade to the next nside
                upgraded_pixels_to_refine.extend(u)
            all_pixels_to_refine.extend([(current_nside*2, pix) for pix in upgraded_pixels_to_refine])

        current_nside = current_nside*2 # test the next nside

    return all_pixels_to_refine


if __name__ == "__main__":
    from optparse import OptionParser
    from load_scan_state import load_cache_state

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

    state_dict = load_cache_state(eventID, cache_dir=options.CACHEDIR)[1]
    pixels = choose_new_pixels_to_scan(state_dict)

    print "got", pixels
    print "number of pixels to scan is", len(pixels)
