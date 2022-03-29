from __future__ import print_function
from __future__ import absolute_import

import os
import shutil
import json
import hashlib
import numpy
import healpy

from icecube import icetray, dataio, dataclasses, astro

import config

def create_pixel_list(nside, area_center_nside=None, area_center_pixel=None, area_num_pixels=None):
    if (area_center_nside is not None or area_center_pixel is not None or area_num_pixels is not None) and \
       (area_center_nside is None or area_center_pixel is None or area_num_pixels is None):
       raise RuntimeError("You have to either set none of the three options area_center_nside,area_center_pixel,area_num_pixels or all of them")

    npixel_max = healpy.nside2npix(nside)

    # just return all pixels if no specific area is requested or the area covers the entire map
    if (area_center_nside is None) or (area_num_pixels >= npixel_max):
        return range(npixel_max)

    # otherwise, build the area iteratively
    pixel_area_sqdeg = healpy.nside2pixarea(nside, degrees=True)
    area_for_requested_pixels_sqdeg = pixel_area_sqdeg*float(area_num_pixels)
    approx_radius = numpy.sqrt(area_for_requested_pixels_sqdeg)/numpy.pi
    print("Building healpix pixel list for nside {} with an area of {} (out of {}) pixels (=={:.2f}sqdeg; radius={:.2f}deg)".format(
        nside, area_num_pixels, npixel_max, area_for_requested_pixels_sqdeg, approx_radius
    ))
    
    # get the center coordinate
    c_x,c_y,c_z = healpy.pix2vec(area_center_nside, area_center_pixel)
    start_pixel = healpy.vec2pix(nside, c_x,c_y,c_z)
    c_x,c_y,c_z = healpy.pix2vec(nside, start_pixel)
    pixel_set = set([start_pixel])
    
    print("start pixel:", start_pixel)
    
    # Create a full list of pixels ordered so that the center pixel is first and the distance to the center is growing.
    # Then crop the list to return the number of requested pixels. This makes sure that we can extend the list later.
    
    pixels = numpy.array(range(npixel_max))
    
    p_x,p_y,p_z = healpy.pix2vec(nside, pixels)
    pixel_space_angles = numpy.arccos(numpy.clip(c_x*p_x + c_y*p_y + c_z*p_z, -1., 1.))
    pixel_num = numpy.array(range(len(pixel_space_angles)), dtype=numpy.float)
    
    # pixels, sorted by distance from the requested pixel; secondary sort key is just the healpix pixel index
    pixel_list_sorted = pixels[numpy.lexsort( (pixel_num, pixel_space_angles) )].tolist()

    return_list = pixel_list_sorted[:area_num_pixels]
    
    print("Pixel set created. It has {} entries (requested entries were {})".format(len(return_list), area_num_pixels))
    
    return return_list
    
def get_event_header(frame_packet):
    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Physics and p_frame.Stop != icetray.I3Frame.Stream('p'):
        raise RuntimeError("no p-frame found at the end of the GCDQp packet")
    if "I3EventHeader" not in p_frame:
        raise RuntimeError("No I3EventHeader in p-frame")

    return p_frame["I3EventHeader"]

def get_event_time(frame_packet):
    return get_event_header(frame_packet).start_time

def get_event_mjd(frame_packet):
    time = get_event_time(frame_packet)
    return time.mod_julian_day_double

def get_event_id(frame_packet):
    header = get_event_header(frame_packet)
    return "run{0:08d}.evt{1:012d}.HESE".format(header.run_id, header.event_id)

def parse_event_id(event_id_string):
    parts = event_id_string.split('.')
    if len(parts) != 3:
        raise RuntimeError("event ID must have 3 parts separated by '.'")

    if not parts[0].startswith("run"):
        raise RuntimeError("event ID run part does not start with \"run\"")
    if not parts[1].startswith("evt"):
        raise RuntimeError("event ID event part does not start with \"evt\"")

    run = int(parts[0][3:])
    event = int(parts[1][3:])
    evt_type = parts[2]
    return (run, event, evt_type)

def load_GCD_frame_packet_from_file(filename, filestager=None):
    read_url = filename
    for GCD_base_dir in config.GCD_base_dirs:
        potential_read_url = os.path.join(GCD_base_dir, filename)
        if os.path.isfile( potential_read_url ):
            read_url = potential_read_url
            break

    if filestager is not None:
        read_url_handle = filestager.GetReadablePath( read_url )
    else:
        read_url_handle = read_url

    frame_packet = []
    i3f = dataio.I3File(str(read_url_handle),'r')
    while True:
        if not i3f.more():
            return frame_packet
        frame = i3f.pop_frame()
        frame_packet.append(frame)

    del read_url_handle

def save_GCD_frame_packet_to_file(frame_packet, filename):
    i3f = dataio.I3File(filename,'w')
    for frame in frame_packet:
        i3f.push(frame)
    i3f.close()
    del i3f

def hash_frame_packet(frame_packet):
    m = hashlib.sha1()
    for frame in frame_packet:
        m.update(frame.dumps())
    return m.hexdigest()

def rewrite_frame_stop(input_frame, new_stream):
    input_frame.purge() # deletes all non-native items

    for key in input_frame.keys():
        input_frame.change_stream(key, new_stream)

    new_frame = icetray.I3Frame(new_stream)
    new_frame.merge(input_frame)
    del input_frame

    return new_frame

def get_MC_truth(frame_packet):
    p_frame = frame_packet[-1]
    if p_frame.Stop != icetray.I3Frame.Stream('p') and p_frame.Stop != icetray.I3Frame.Physics:
        raise RuntimeError("last frame of GCDQp is neither Physics not 'p'")

    q_frame = frame_packet[-2]
    if q_frame.Stop != icetray.I3Frame.DAQ:
        raise RuntimeError("second to last frame of GCDQp is not type Q")

    if "I3MCTree_preMuonProp" not in q_frame:
        return None, None
    mc_tree = q_frame["I3MCTree_preMuonProp"]

    # find the muon
    muon = None
    for particle in mc_tree:
        if particle.type not in [dataclasses.I3Particle.ParticleType.MuPlus, dataclasses.I3Particle.ParticleType.MuMinus]: continue
        if muon is not None:
            print("More than one muon in MCTree")
            if particle.energy < muon.energy: continue
        muon = particle

    if muon is None:
        # must be NC
        return None, None

    # get event time
    mjd = get_event_mjd(frame_packet)

    # convert to RA and dec
    ra, dec = astro.dir_to_equa( muon.dir.zenith, muon.dir.azimuth, mjd )
    ra = float(ra)
    dec = float(dec)
    dec = dec

    return ra, dec
