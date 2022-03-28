# fmt: off
# isort: skip_file

import io
import os
import numpy
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import healpy
from astropy.io import ascii

import pickle as Pickle
from icecube import icetray, dataclasses, dataio
from icecube.astro import angular_distance

from skymap_scanner.utils import parse_event_id, get_event_mjd
from skymap_scanner import config

#from . import slack_tools

from matplotlib.axes import Axes
from matplotlib import text
from matplotlib.ticker import Formatter, FixedFormatter, FixedLocator
from matplotlib.transforms import Transform, Affine2D
from matplotlib.projections import projection_registry
from matplotlib.projections.geo import MollweideAxes
import matplotlib.patheffects as path_effects
import matplotlib.units as units
import astropy.io.fits as pyfits
from astropy.coordinates import SkyCoord

import meander


def hp_ticklabels(zoom=False, lonra=None, latra=None, rot=None, bounds=None):
    """ labels coordinates on a healpy map
    zoom: indicates zoomed-in cartview
    lonra: longitude range of zoomed-in map
    latra: latitude range of zoom-in map
    rot: center of zoomed in map
    """
    lower_lon, upper_lon, lower_lat, upper_lat = bounds
    # coordinate labels
    ax = plt.gca()
    if zoom:
        # location of other, fixed coordinate
        lon_offset = rot[0]+lonra[0] - 0.025*(lonra[1]-lonra[0])
        lat_offset = rot[1]+latra[0] - 0.05*(latra[1]-latra[0])
        # lonlat coordinates for labels
        min_lon = numpy.round(lon_offset/2.)*2. - 2
        max_lon = lon_offset+lonra[1]-lonra[0] + 2
        lons = numpy.arange(min_lon, max_lon, 2)
        
        min_lat = numpy.round(lat_offset/2.)*2. - 2
        max_lat = lat_offset+latra[1]-latra[0] + 2
        lats = numpy.arange(min_lat, max_lat, 2)

        lon_set = []
        for lon in lons:
            if lon > lower_lon and lon < upper_lon:
                lon_set.append(lon)

        lat_set = []
        for lat in lats:
            if lat > lower_lat and lat < upper_lat:
                lat_set.append(lat)

        lons = numpy.array(lon_set)
        lats = numpy.array(lat_set)
        lat_offset = rot[1]+latra[1] + 0.05*(latra[1]-latra[0])
    else:
        lon_offset = -180
        lat_offset = 0

        # lonlat coordinates for labels
        lons = numpy.arange(-150, 181, 30)
        lats = numpy.arange(-90, 91, 30)

    # actual text at those coordinates
    llats = -lats

    # white outline around text
    pe = [path_effects.Stroke(linewidth=1.5, foreground='white'),
          path_effects.Normal()]
    for _ in zip(lats, llats):
        healpy.projtext(lon_offset, _[0], "{:.0f}$^\circ$".format(_[1]),
                    lonlat=True, path_effects=pe, fontsize=10)
    if zoom:
        for _ in lons:
            healpy.projtext(_, lat_offset,
                        "{:.0f}$^\circ$".format(_), lonlat=True,
                        path_effects=pe, fontsize=10)
    else:
        ax.annotate(r"$\bf{-180^\circ}$", xy=(1.7, 0.625), size="medium")
        ax.annotate(r"$\bf{180^\circ}$", xy=(-1.95, 0.625), size="medium")
    ax.annotate("Equatorial", xy=(0.8, -0.15),
                size="medium", xycoords="axes fraction")

def plot_catalog(master_map, cmap, lower_ra, upper_ra, lower_dec, upper_dec,
        cmap_min=0., cmap_max=250.):
    """"Plots the 4FGL catalog in a color that contrasts with the background
    healpix map"""
    hdu = pyfits.open('/cvmfs/icecube.opensciencegrid.org/users/followup/reference_catalogues/gll_psc_v27.fit')
    fgl = hdu[1]
    pe = [path_effects.Stroke(linewidth=0.5, foreground=cmap(0.0)),
        path_effects.Normal()]

    fname_i = numpy.array(fgl.data['Source_Name'])
    fra_i = numpy.array(fgl.data['RAJ2000'])*numpy.pi/180.
    fdec_i = numpy.array(fgl.data['DEJ2000'])*numpy.pi/180.
    fgl_mask = numpy.logical_and(numpy.logical_and(fra_i > lower_ra, fra_i < upper_ra), numpy.logical_and(fdec_i > lower_dec, fdec_i < upper_dec))
    flon_i = fra_i
    flat_i = -fdec_i

    def color_filter(lon, lat):
        vals = healpy.get_interp_val(master_map, lon, lat, lonlat=True)
        vals = (healpy.get_interp_val(master_map, lon, lat, lonlat=True) - cmap_min)/(cmap_max-cmap_min)
        vals = numpy.where(vals < 0.0, 0.0, vals)
        vals = numpy.where(vals > 1.0, 1.0, vals)
        vals = numpy.round(1.0-vals)
        return vals

    healpy.projscatter(
        flon_i[fgl_mask]*180./numpy.pi,
        flat_i[fgl_mask]*180./numpy.pi,
        lonlat=True,
        c=cmap(color_filter(flon_i[fgl_mask]*180./numpy.pi, flat_i[fgl_mask]*180./numpy.pi)),
        marker='o',
        s=10)
    for i in range(len(fgl_mask)):
        if not fgl_mask[i]:
            continue
        healpy.projtext(flon_i[i]*180./numpy.pi,
                flat_i[i]*180./numpy.pi,
                fname_i[i],
                lonlat=True,
                color = cmap(1.0),
                fontsize=6,
                path_effects=pe)
    del fgl

def format_fits_header(event_id_string, state_dict, ra, dec, uncertainty):
    '''Prepare some of the relevant event information for 
    a fits file header'''
    run_id, event_id, event_type = parse_event_id(event_id_string)
    mjd = get_event_mjd(state_dict)

    header = [
        ('RUNID', run_id), 
        ('EVENTID', event_id),
        ('SENDER', 'IceCube Collaboration'),
        ('EventMJD', mjd),
        ('I3TYPE', '%s'%event_type,'Alert Type'),
        ('RA', numpy.round(ra,2),'Degree'),
        ('DEC', numpy.round(dec,2),'Degree'),
        ('RA_PLUS', numpy.round(uncertainty[0][1],2),
            '90% containment error high'),
        ('RA_MIN', numpy.round(numpy.abs(uncertainty[0][0]),2),
            '90% containment error low'),
        ('DEC_PLUS', numpy.round(uncertainty[1][1],2),
            '90% containment error high'),
        ('DEC_MIN', numpy.round(numpy.abs(uncertainty[1][0]),2),
            '90% containment error low'),
        ('COMMENTS', '50%(90%) uncertainty location' \
            + ' => Change in 2LLH of 22.2(64.2)'),
        ('NOTE', 'Please ignore pixels with infinite or NaN values.' \
            + ' They are rare cases of the minimizer failing to converge')
        ]
    return header

def create_plot_zoomed(event_id_string, state_dict, outdir, systematics=True, 
    extra_ra=numpy.nan, extra_dec=numpy.nan, extra_radius=numpy.nan,
    log_func=None, upload_func=None, final_channels=None):

    if log_func is None:
        def log_func(x):
            print(x)

    if upload_func is None:
        def upload_func(file_buffer, name, title):
            pass
            
    if final_channels is None:
        final_channels=["#test_messaging"]

    y_inches = 3.85
    x_inches = 6.
    dpi = 1200.
    xsize = x_inches*dpi
    ysize = xsize/2.

    lonra=[-10.,10.]
    latra=[-10.,10.]

    if "nsides" not in state_dict:
        raise RuntimeError("\"nsides\" not in dictionary..")

    run_id, event_id, event_type = parse_event_id(event_id_string)

    mjd = get_event_mjd(state_dict)

    plot_title = "Run: {0} Event: {1} Type: {2} MJD: {3}".format(run_id, event_id, event_type, mjd)

    if systematics is not True:
        plot_filename = outdir + event_id_string + ".plot_zoomed_wilks.pdf"
    else:
        plot_filename = outdir + event_id_string + ".plot_zoomed.pdf"
    print("saving plot to {0}".format(plot_filename))

    nsides = list(state_dict["nsides"].keys())
    print("available nsides: {0}".format(nsides))

    grid_map = dict()
    max_nside = max(nsides)
    master_map = numpy.full(healpy.nside2npix(max_nside), numpy.nan)

    for nside in sorted(nsides):
        npix = healpy.nside2npix(nside)

        map_data = state_dict["nsides"][nside]
        pixels = numpy.array(list(map_data.keys()))
        values = [map_data[p]['llh'] for p in pixels.tolist()]
        this_map = numpy.full(npix, numpy.nan)
        this_map[pixels] = values
        if nside < max_nside:
            this_map = healpy.ud_grade(this_map, max_nside)
        mask = numpy.logical_and(~numpy.isnan(this_map), numpy.isfinite(this_map))
        master_map[mask] = this_map[mask]

        for pixel, pixel_data in state_dict["nsides"][nside].items():
            value = pixel_data['llh']
            if numpy.isfinite(value) and not numpy.isnan(value):
                tmp_theta, tmp_phi = healpy.pix2ang(nside, pixel)
                tmp_dec = tmp_theta - numpy.pi/2.
                tmp_ra = tmp_phi
                grid_map[(tmp_dec, tmp_ra)] = value
        print("done with map for nside {0}...".format(nside))

    grid_dec = []; grid_ra = []; grid_value = []

    for (dec, ra), value in grid_map.items():
        grid_dec.append(dec); grid_ra.append(ra)
        grid_value.append(value)
    grid_dec = numpy.asarray(grid_dec)
    grid_ra = numpy.asarray(grid_ra)
    grid_value = numpy.asarray(grid_value)

    sorting_indices = numpy.argsort(grid_value)
    grid_value = grid_value[sorting_indices]
    grid_dec = grid_dec[sorting_indices]
    grid_ra = grid_ra[sorting_indices]

    min_value = grid_value[0]
    minDec = grid_dec[0]
    minRA = grid_ra[0]

    print("min  RA:", minRA *180./numpy.pi, "deg,", minRA*12./numpy.pi, "hours")
    print("min dec:", minDec*180./numpy.pi, "deg")

    # renormalize
    grid_value = grid_value - min_value
    min_value = 0.

    # show 2 * delta_LLH 
    grid_value = grid_value * 2.
    
    # Do same for the healpy map
    master_map[numpy.isinf(master_map)] = numpy.nan
    master_map -= numpy.nanmin(master_map)
    master_map *= 2.

    print("preparing plot: {0}...".format(plot_filename))

    cmap = matplotlib.cm.viridis_r
    cmap.set_under('w')
    cmap.set_bad(alpha=1., color=(1.,0.,0.)) # make NaNs bright red

    # Calculate the contours
    if systematics:
        # from Pan-Starrs event 127852
        contour_levels = (numpy.array([22.2, 64.2])+min_value) # these are values determined from MC by Will on the TS (2*LLH)
        contour_labels = [r'50% (IC160427A syst.)', r'90% (IC160427A syst.)']
        contour_colors=['k', 'r']
    else:
        # # Wilk's
        contour_levels = (numpy.array([1.39, 4.61, 11.83, 28.74])+min_value)[1:]
        contour_labels = [r'50%', r'90%', r'3$\sigma$', r'5$\sigma$'][1:]
        contour_colors=['0.5', 'k', 'r', 'g'][1:]

    sample_points = numpy.array([grid_dec + numpy.pi/2., grid_ra]).T
    # Call meander module to find contours
    contours_by_level = meander.spherical_contours(sample_points,
        grid_value, contour_levels
        )
    # Check for RA values that are out of bounds
    for level in contours_by_level:
        for contour in level:
            contour.T[1] = numpy.where(contour.T[1] < 0., 
                contour.T[1] + 2.*numpy.pi, contour.T[1]
                )

    # Find the rough extent of the contours to bound the plot
    contours = contours_by_level[-1]
    ra_plus = None
    ra = minRA * 180./numpy.pi
    dec = minDec * 180./numpy.pi
    for contour in contours:
        theta, phi = contour.T
        if ra_plus is None:
            ra_plus = numpy.max(phi)*180./numpy.pi - ra
            ra_minus = numpy.min(phi)*180./numpy.pi - ra
            dec_plus = (numpy.max(theta)-numpy.pi/2.)*180./numpy.pi - dec
            dec_minus = (numpy.min(theta)-numpy.pi/2.)*180./numpy.pi - dec
        else:
            ra_plus = max(ra_plus, numpy.max(phi)*180./numpy.pi - ra)
            ra_minus = min(ra_minus, numpy.min(phi)*180./numpy.pi - ra)
            dec_plus = max(dec_plus, (numpy.max(theta)-numpy.pi/2.)*180./numpy.pi - dec)
            dec_minus = min(dec_minus, (numpy.min(theta)-numpy.pi/2.)*180./numpy.pi - dec)
    lonra = [min(-3., ra_minus), max(3., ra_plus)]
    latra = [min(-2., dec_minus), max(2., dec_plus)]
    
    #Begin the figure 
    plt.clf()
    # Rotate into healpy coordinates
    lon, lat = numpy.degrees(minRA), -numpy.degrees(minDec)
    healpy.cartview(map=master_map,
        min=0., #min 2DeltaLLH value for colorscale
        max=250., #max 2DeltaLLH value for colorscale
        rot=(lon,lat,0.), cmap=cmap, hold=True,
        cbar=None, lonra=lonra, latra=[-latra[1], -latra[0]],
        unit=r"$-2 \Delta \ln (L)$",
        )
    #plt.title(plot_title)
    plt.gca().invert_yaxis()

    fig = plt.gcf()
    ax = plt.gca()
    image = ax.get_images()[0]
    # Place colorbar by hand
    cb = fig.colorbar(image, ax=ax, orientation='horizontal', aspect=50)
    cb.ax.xaxis.set_label_text(r"$-2 \Delta \ln (L)$")

    # Plot the best-fit location
    # This requires some more coordinate transformations
    healpy.projplot(minDec + numpy.pi/2., minRA, 
        '*', ms=5, label=r'scan best fit', color='black', zorder=2)

    # Use Green's theorem to compute the area
    # enclosed by the given contour.
    def area(vs):
        a = 0
        x0,y0 = vs[0]
        for [x1,y1] in vs[1:]:
            dx = x1-x0
            dy = y1-y0
            a += 0.5*(y0*dx - x0*dy)
            x0 = x1
            y0 = y1
        return a
    
    # Plot the contours
    for contour_level, contour_label, contour_color, contours in zip(contour_levels, 
        contour_labels, contour_colors, contours_by_level):
        contour_area = 0 
        for contour in contours:
            contour_area += area(contour)
        contour_area = abs(contour_area)
        contour_area *= (180.*180.)/(numpy.pi*numpy.pi) # convert to square-degrees
        contour_label = contour_label + ' - area: {0:.2f} sqdeg'.format(
            contour_area)
        first = True
        for contour in contours:
            theta, phi = contour.T
            if first:
                healpy.projplot(theta, phi, linewidth=2, c=contour_color, 
                    label=contour_label)
            else:
                healpy.projplot(theta, phi, linewidth=2, c=contour_color)
            first = False

    # Add some grid lines
    healpy.graticule(dpar=2, dmer=2, force=True) 

    # Set some axis limits
    lower_ra = minRA + numpy.radians(lonra[0])
    upper_ra = minRA + numpy.radians(lonra[1])
    lower_dec = minDec + numpy.radians(latra[0])
    upper_dec = minDec + numpy.radians(latra[1])

    lower_lon = numpy.degrees(lower_ra)
    upper_lon = numpy.degrees(upper_ra)
    tmp_lower_lat = -1.*numpy.degrees(lower_dec)
    tmp_upper_lat = -1.*numpy.degrees(upper_dec)
    lower_lat = min(tmp_lower_lat, tmp_upper_lat)
    upper_lat = max(tmp_lower_lat, tmp_upper_lat)

    # Label the axes
    hp_ticklabels(zoom=True, lonra=lonra, latra=[-latra[1], -latra[0]],
        rot=(lon,lat,0), 
        bounds=(lower_lon, upper_lon, lower_lat, upper_lat))

    # Overlay 4FGL sources
    plot_catalog(master_map, cmap, lower_ra, upper_ra, lower_dec, upper_dec)
    plt.title(plot_title) 

    # Approximate contours as rectangles
    if systematics is True:
        ra = minRA * 180./numpy.pi
        dec = minDec * 180./numpy.pi
        for l, contours in enumerate(contours_by_level):
            ra_plus = None
            for contour in contours:
                theta, phi = contour.T
                if ra_plus is None:
                    ra_plus = numpy.max(phi)*180./numpy.pi - ra
                    ra_minus = numpy.min(phi)*180./numpy.pi - ra
                    dec_plus = (numpy.max(theta)-numpy.pi/2.)*180./numpy.pi - dec
                    dec_minus = (numpy.min(theta)-numpy.pi/2.)*180./numpy.pi - dec
                else:
                    ra_plus = max(ra_plus, numpy.max(phi)*180./numpy.pi - ra)
                    ra_minus = min(ra_minus, numpy.min(phi)*180./numpy.pi - ra)
                    dec_plus = max(dec_plus, (numpy.max(theta)-numpy.pi/2.)*180./numpy.pi - dec)
                    dec_minus = min(dec_minus, (numpy.min(theta)-numpy.pi/2.)*180./numpy.pi - dec)
            contain_txt = "Approximating the {0}% error region as a rectangle, we get:".format(["50", "90"][l]) + " \n" + \
                          "\t RA = {0:.2f} + {1:.2f} - {2:.2f}".format(
                              ra, ra_plus, numpy.abs(ra_minus)) + " \n" + \
                          "\t Dec = {0:.2f} + {1:.2f} - {2:.2f}".format(
                              dec, dec_plus, numpy.abs(dec_minus))                
            log_func(contain_txt)
        plot_bounding_box = True
        if plot_bounding_box:
            bounding_ras = []; bounding_decs = []
            # lower bound
            bounding_ras.extend(list(numpy.linspace(ra+ra_minus, 
                ra+ra_plus, 10)))
            bounding_decs.extend([dec+dec_minus]*10)
            # right bound
            bounding_ras.extend([ra+ra_plus]*10)
            bounding_decs.extend(list(numpy.linspace(dec+dec_minus,
                dec+dec_plus, 10)))
            # upper bound
            bounding_ras.extend(list(numpy.linspace(ra+ra_plus,
                ra+ra_minus, 10)))
            bounding_decs.extend([dec+dec_plus]*10)
            # left bound
            bounding_ras.extend([ra+ra_minus]*10)
            bounding_decs.extend(list(numpy.linspace(dec+dec_plus,
                dec+dec_minus,10)))
            # join end to beginning
            bounding_ras.append(bounding_ras[0])
            bounding_decs.append(bounding_decs[0])
            bounding_ras = numpy.asarray(bounding_ras)
            bounding_decs = numpy.asarray(bounding_decs)
            bounding_phi = numpy.radians(bounding_ras)
            bounding_theta = numpy.radians(bounding_decs) + numpy.pi/2.
            bounding_contour = numpy.array([bounding_theta, bounding_phi])
            bounding_contour_area = 0.
            bounding_contour_area = area(bounding_contour.T)
            bounding_contour_area *= (180.*180.)/(numpy.pi*numpy.pi) # convert to square-degrees
            contour_label = r'90% Bounding rectangle' + ' - area: {0:.2f} sqdeg'.format(
                bounding_contour_area)
            healpy.projplot(bounding_theta, bounding_phi, linewidth=0.75, 
                c='r', linestyle='dashed', label=contour_label)

        # Output contours in RA, dec instead of theta, phi
        saving_contours = []
        for contours in contours_by_level:
            saving_contours.append([])
            for contour in contours:
                saving_contours[-1].append([])
                theta, phi = contour.T
                ras = phi
                decs = theta - numpy.pi/2.
                for tmp_ra, tmp_dec in zip(ras, decs):
                    saving_contours[-1][-1].append([tmp_ra, tmp_dec])
        # Dump the whole contour
        path = outdir + event_id_string + ".contour.pkl"
        print("Saving contour to", path)
        with open(path, "wb") as f:
            Pickle.dump(saving_contours, f)
        
        # Save the individual contours, send messages
        for i, val in enumerate(["50", "90"]):
            ras = list(numpy.asarray(saving_contours[i][0]).T[0])
            decs = list(numpy.asarray(saving_contours[i][0]).T[1])
            tab = {"ra (rad)": ras, "dec (rad)": decs}
            savename = outdir + event_id_string + ".contour_" + val + ".txt"
            try:
                ascii.write(tab, savename, overwrite=True)
                print("Dumping to", savename)
                for j, ch in enumerate(final_channels):
                    output = io.StringIO()
                    #output = str.encode(savename)
                    ascii.write(tab, output, overwrite=True)
                    output.seek(0) 
                    config.slack_channel=ch
                    print(upload_func(output, savename, savename))
                    output.truncate(0) 
                    del output
            except OSError:
                log_func("Memory Error prevented contours from being written")

        uncertainty = [(ra_minus, ra_plus), (dec_minus, dec_plus)]
        fits_header = format_fits_header(event_id_string, state_dict, 
            numpy.degrees(minRA), numpy.degrees(minDec), uncertainty,
           )
        mmap_nside = healpy.get_nside(master_map)

        # Pixel numbers as is gives a map that is reflected
        # about the equator. This is all deal with self-consistently
        # here but we need to correct before outputting a fits file
        def fixpixnumber(nside,pixels):
            th_o, phi_o = healpy.pix2ang(nside, pixels)
            dec_o = th_o - numpy.pi/2
            th_fixed = numpy.pi/2 - dec_o 
            pix_fixed = healpy.ang2pix(nside, th_fixed, phi_o)
            return pix_fixed
        pixels = numpy.arange(len(master_map))
        nside = healpy.get_nside(master_map)
        new_pixels = fixpixnumber(nside, pixels)
        equatorial_map = master_map[new_pixels]

        healpy.write_map(f"{outdir}{event_id_string}.skymap_nside_{mmap_nside}.fits.gz",
            equatorial_map, coord = 'C', column_names = ['2LLH'],
            extra_header = fits_header, overwrite=True)

    # Plot the original online reconstruction location
    if numpy.sum(numpy.isnan([extra_ra, extra_dec, extra_radius])) == 0: 

        def circular_contour(ra, dec, sigma, nside):
            """For plotting circular contours on skymaps
            ra, dec, sigma all expected in radians
            """
            dec = numpy.pi/2. - dec
            sigma = numpy.rad2deg(sigma)
            delta, step, bins = 0, 0, 0
            delta= sigma/180.0*numpy.pi
            step = 1./numpy.sin(delta)/10.
            bins = int(360./step)
            Theta = numpy.zeros(bins+1, dtype=numpy.double)
            Phi = numpy.zeros(bins+1, dtype=numpy.double)
            # define the contour
            for j in range(0,bins) :
                phi = j*step/180.*numpy.pi
                vx = numpy.cos(phi)*numpy.sin(ra)*numpy.sin(delta) + numpy.cos(ra)*(numpy.cos(delta)*numpy.sin(dec) + numpy.cos(dec)*numpy.sin(delta)*numpy.sin(phi))
                vy = numpy.cos(delta)*numpy.sin(dec)*numpy.sin(ra) + numpy.sin(delta)*(-numpy.cos(ra)*numpy.cos(phi) + numpy.cos(dec)*numpy.sin(ra)*numpy.sin(phi))
                vz = numpy.cos(dec)*numpy.cos(delta) - numpy.sin(dec)*numpy.sin(delta)*numpy.sin(phi)
                idx = healpy.vec2pix(nside, vx, vy, vz)
                DEC, RA = healpy.pix2ang(nside, idx)
                Theta[j] = DEC
                Phi[j] = RA
            Theta[bins] = Theta[0]
            Phi[bins] = Phi[0]
            return Theta, Phi

        dist = angular_distance(minRA, minDec, extra_ra * numpy.pi/180., extra_dec * numpy.pi/180.)
        print("Millipede best fit is", dist /(numpy.pi * extra_radius/(1.177 * 180.)), "sigma from reported best fit")        

        extra_ra_rad = numpy.radians(extra_ra)
        extra_dec_rad = numpy.radians(extra_dec)
        extra_radius_rad = numpy.radians(extra_radius)
        extra_lon = extra_ra_rad
        extra_lat = -extra_dec_rad

        healpy.projscatter(numpy.degrees(extra_lon), numpy.degrees(extra_lat),
            lonlat=True, c='m', marker='x', s=20, label=r'Reported online (50%, 90%)')
        for cont_lev, cont_scale, cont_col, cont_sty in zip(['50', '90.'], 
                [1., 2.1459/1.177], ['m', 'm'], ['-', '--']):
            spline_contour = circular_contour(extra_ra_rad, extra_dec_rad,
                extra_radius_rad*cont_scale, healpy.get_nside(master_map))
            spline_lon = spline_contour[1]
            spline_lat = -1.*(numpy.pi/2. - spline_contour[0])
            healpy.projplot(numpy.degrees(spline_lon), numpy.degrees(spline_lat), 
                lonlat=True, linewidth=2., color=cont_col, 
                linestyle=cont_sty)

    plt.legend(fontsize=6, loc="lower left")

    # For vertical events, calculate the area with the number of pixels
    # In the healpy map   
    for lev in contour_levels[-1:]:
        area_per_pix = healpy.nside2pixarea(healpy.get_nside(master_map))
        num_pixs = numpy.count_nonzero(master_map[~numpy.isnan(master_map)] < lev)
        healpy_area = num_pixs * area_per_pix * (180./numpy.pi)**2.
    print("Contour Area (90%):", contour_area, "degrees (cartesian)", 
        healpy_area, "degrees (scaled)")

    # Save the figure
    print("saving: {0}...".format(plot_filename))
    #ax.invert_xaxis()
    fig.savefig(plot_filename, dpi=dpi, transparent=True)

    # # use io.BytesIO to save this into a memory buffer
    # imgdata = io.BytesIO()
    # fig.savefig(imgdata, format='png', dpi=dpi, transparent=True)
    # imgdata.seek(0)

    print("done.")

    if systematics is True:
        title = "Millipede contour, assuming IC160427A systematics:"
    else:
        title = "Millipede contour, assuming Wilk's Theorum:"

    if systematics is True:
        for i, ch in enumerate(final_channels):
            imgdata = io.BytesIO()
            fig.savefig(imgdata, format='png', dpi=600, transparent=True)
            imgdata.seek(0)

            savename = plot_filename[:-4] + ".png"
            print(savename)
            config.slack_channel=ch
            upload_func(imgdata, savename, title)
    else:
        imgdata = io.BytesIO()
        fig.savefig(imgdata, format='png', dpi=600, transparent=True)
        imgdata.seek(0)

        savename = plot_filename[:-4] + ".png"
        print(savename)
        config.slack_channel=final_channels[0]
        upload_func(imgdata, savename, title)
    
    plt.close()
    # imgdata.truncate(0)
    # del imgdata


def loop_over_plots(eventID, cache_dir, outdir='/home/followup/output_plots/', ra=numpy.nan, dec=numpy.nan, radius=numpy.nan, state_dict=None, log_func=None, upload_func=None, final_channels=None):
    from skymap_scanner.load_scan_state import load_cache_state
    # get the file stager instance

    if state_dict is None:
   
        stagers = dataio.get_stagers()

        eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=cache_dir)

    for i, syst in enumerate([True, False]):
        create_plot_zoomed(eventID, state_dict, outdir, syst, ra, dec, radius, log_func, upload_func, final_channels)
#        if upload_func is not None:
#            contour = ["IC160427A", "Wilk's"][i]
#            upload_func(plot_png_buffer, "skymap_{0}.png".format(eventID),
#                       "Skymap of {0} assuming {1} contours".format(eventID, contour))

if __name__ == "__main__":
    from optparse import OptionParser
#    from skymap_scanner.load_scan_state import load_cache_state

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("--ra", action="store", type="float", dest="RA",
        default=numpy.nan, help="Right Ascension in degrees")
    parser.add_option("--dec", action="store", type="float", dest="DEC",
        default=numpy.nan, help="Declination in degrees")
    parser.add_option("--radius", action="store", type="float",dest="RADIUS",
        default=numpy.nan, help="50% error radius in degrees") 
    parser.add_option("-o", "--path-to-output", action="store", type="string",dest="OUTDIR",
        default="/home/followup/output_plots/", help="The directory where the output will be saved")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    loop_over_plots(eventID, options.CACHEDIR, options.OUTDIR, options.RA, options.DEC, options.RADIUS)

    # get the file stager instance
#    stagers = dataio.get_stagers()

#   eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=options.CACHEDIR)
#  for syst in [True, False]:
#     plot_png_buffer = create_plot_zoomed(eventID, state_dict, syst, options.RA, options.DEC, options.RADIUS)
# # we have a buffer containing a valid png file now, post it to Slack
# slack_tools.upload_file(plot_png_buffer, "skymap.png", "Skymap!")
