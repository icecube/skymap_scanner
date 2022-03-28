# fmt: off
# isort: skip_file

from __future__ import print_function
from __future__ import absolute_import

import io
import os
import numpy
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import healpy
from astropy.io import ascii

import cPickle as Pickle
from icecube import icetray, dataclasses, dataio
from icecube.astro import angular_distance

from skymap_scanner.utils import parse_event_id, get_event_mjd
from skymap_scanner import config

# from . import slack_tools

from matplotlib.axes import Axes
from matplotlib import text
from matplotlib.ticker import Formatter, FixedFormatter, FixedLocator
from matplotlib.transforms import Transform, Affine2D
from matplotlib.projections import projection_registry
from matplotlib.projections.geo import MollweideAxes
import matplotlib.units as units
import astropy.io.fits as pyfits
from astropy.coordinates import SkyCoord
##
# Mollweide axes with phi axis flipped and in hours from 24 to 0 instead of
#         in degrees from -180 to 180.
class RaFormatter(Formatter):
    def __init__(self):
        pass

    def __call__(self, x, pos=None):
        hours = (x / numpy.pi) * 12.
        minutes = hours - int(hours)
        hours = int(hours)
        minutes = minutes * 60.

        seconds = minutes - int(minutes)
        minutes = int(minutes)
        seconds = seconds*60.
        seconds = int(seconds)

        return r"%0.0f$^\mathrm{h}$%0.0f$^\prime$%0.0f$^{\prime\prime}$" % (hours, minutes, seconds)

class DecFormatter(Formatter):
    def __init__(self):
        pass

    def __call__(self, x, pos=None):
        degrees = (x / numpy.pi) * 180.
        return r"$%0.1f^\circ$" % (degrees)
        # return r"%0.0f$^\circ$" % (degrees)

def create_plot_zoomed(event_id_string, state_dict, systematics=True, extra_ra=numpy.nan, extra_dec=numpy.nan, extra_radius=numpy.nan, log_func=None, upload_func=None, final_channels=None):

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

    plot_title = "Run: {0} Event {1}: Type: {2} MJD: {3}".format(run_id, event_id, event_type, mjd)

    if systematics is not True:
        plot_filename = event_id_string + ".plot_zoomed_wilks.pdf"
    else:
        plot_filename = event_id_string + ".plot_zoomed.pdf"
    print("saving plot to {0}".format(plot_filename))

    nsides = state_dict["nsides"].keys()
    print("available nsides: {0}".format(nsides))

    maps = []
    min_value = numpy.nan
    max_value = numpy.nan
    minRA=0.
    minDec=0.

    # theta = numpy.linspace(numpy.pi, 0., ysize)
    dec = numpy.linspace(-numpy.pi/2., numpy.pi/2., ysize)

    # phi   = numpy.linspace(0., 2.*numpy.pi, xsize)
    ra = numpy.linspace(0., 2.*numpy.pi, xsize)

    # project the map to a rectangular matrix xsize x ysize
    RA, DEC = numpy.meshgrid(ra, dec)

    grid_map = None

    # now plot maps above each other
    for nside in sorted(nsides):
        print("constructing map for nside {0}...".format(nside))
        # grid_pix = healpy.ang2pix(nside, THETA, PHI)
        grid_pix = healpy.ang2pix(nside, DEC + numpy.pi/2., RA)
        this_map = numpy.ones(healpy.nside2npix(nside))*numpy.inf

        for pixel, pixel_data in state_dict["nsides"][nside].iteritems():
            value = pixel_data['llh']
            if numpy.isfinite(value):
                if numpy.isnan(min_value) or value < min_value:
                    minDec, minRA = healpy.pix2ang(nside, pixel)
                    minDec = minDec - numpy.pi/2.
                    min_value = value
                if numpy.isnan(max_value) or value > max_value:
                    max_value = value
            # if nside in [8,64]: value=numpy.nan
            this_map[pixel] = value

        if grid_map is None:
            grid_map = this_map[grid_pix]
        else:
            grid_map = numpy.where( numpy.isfinite(this_map[grid_pix]), this_map[grid_pix], grid_map)

        del this_map

        print("done with map for nside {0}...".format(nside))

    # clean up
    del grid_pix

    print("min  RA:", minRA *180./numpy.pi, "deg,", minRA*12./numpy.pi, "hours")
    print("min dec:", minDec*180./numpy.pi, "deg")

    # renormalize
    grid_map = grid_map - min_value
    max_value = max_value - min_value
    min_value = 0.

    # show 2*delta_LLH (the TS used by Will)
    grid_map = grid_map * 2.

    grid_map = numpy.ma.masked_invalid(grid_map)

    max_value_zoomed = min_value+3000

    # max_value_zoomed = max_value

    print("preparing plot: {0}...".format(plot_filename))

    # the color map to use
    cmap = matplotlib.cm.cubehelix_r
    cmap.set_under(alpha=0.) # make underflows transparent
    # cmap.set_over(alpha=0.)  # make overflows transparent
    cmap.set_bad(alpha=1., color=(1.,0.,0.)) # make NaNs bright red

    # prepare the figure canvas
    fig = plt.figure(figsize=[x_inches,y_inches])
    ax = fig.add_subplot(111) #,projection='cartesian')

    if True:
        # rasterized makes the map bitmap while the labels remain vectorial
        # flip longitude to the astro convention
        image = ax.pcolormesh(ra, dec, grid_map, vmin=min_value, vmax=max_value_zoomed, rasterized=True, cmap=cmap)
        # ax.set_xlim(numpy.pi, -numpy.pi)

    # from Pan-Starrs event 127852
    contour_levels = (numpy.array([22.2, 64.2])+min_value) # these are values determined from MC by Will on the TS (2*LLH)
    contour_labels = [r'50% (IC160427A syst.)', r'90% (IC160427A syst.)']
    # contour_labels = [r'50%', r'90%']
    contour_colors=['k', 'r']

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
    
    if systematics is not True:
        # # Wilk's
        contour_levels = (numpy.array([1.39, 4.61, 11.83, 28.74])+min_value)[1:]
        contour_labels = [r'50%', r'90%', r'3$\sigma$', r'5$\sigma$'][1:]
        contour_colors=['0.5', 'k', 'r', 'g'][1:]

    CS = ax.contour(ra, dec, grid_map, levels=contour_levels, colors=contour_colors)
    ax.clabel(CS, inline=False, fontsize=12, fmt=dict(zip(contour_levels, contour_labels)))
    
    if systematics is True:
        for l in range(2):
            decs_90 = [x[:,1] for x in CS.allsegs[l]]
            dec_p = max([max(x) for x in decs_90])
            dec_m = min([min(x) for x in decs_90])
            ras_90 = [x[:,0] for x in CS.allsegs[l]]
            ra_p = max([max(x) for x in ras_90])
            ra_m = min([min(x) for x in ras_90])
            contain_txt = "Approximating the {0}% error region as a rectangle, we get:".format(["50", "90"][l]) + " \n" + \
                          "\t RA = {0:.2f} + {1:.2f} - {2:.2f}".format(numpy.degrees(minRA), numpy.degrees(ra_p-minRA), numpy.degrees(minRA-ra_m)) + " \n" + \
                          "\t Dec = {0:.2f} + {1:.2f} - {2:.2f}".format(numpy.degrees(minDec), numpy.degrees(dec_p-minDec), numpy.degrees(minDec-dec_m))

            log_func(contain_txt)

        path = event_id_string + ".contour.pkl"
        print("Saving contour to", path)
        with open(path, "wb") as f:
            Pickle.dump(CS.allsegs, f)
        
        for i, val in enumerate(["50", "90"]):
            ras = CS.allsegs[i][0][:,0]
            decs = CS.allsegs[i][0][:,1]
            tab = {"ra (rad)": ras, "dec (rad)": decs}
            savename = event_id_string + ".contour_" + val + ".txt"
            try:
                ascii.write(tab, savename)
                print("Dumping to", savename)
                for i, ch in enumerate(final_channels):
                    output = io.BytesIO()
                    ascii.write(tab, output, overwrite=True)
                    output.seek(0)
                    config.slack_channel=ch
                    print(upload_func(output, savename, savename))
                output.truncate(0)
                del output
            except OSError:
                log_func("Memory Error prevented contours from being written")

    for i in range(len(contour_labels)):
        vs = CS.collections[i].get_paths()[0].vertices
        # Compute area enclosed by vertices.
        a = area(vs) # will be in square-radians
        a = a*(180.*180.)/(numpy.pi*numpy.pi) # convert to square-degrees

        CS.collections[i].set_label(contour_labels[i] + ' - area: {0:.2f}sqdeg'.format(a))

    ax.scatter(minRA, minDec, s=20, marker='s', color='black', label=r'scan best-fit', zorder=2)

    if numpy.sum(numpy.isnan([extra_ra, extra_dec, extra_radius])) == 0: 

        def error_circle_radius(dec, radius):
            """Approximate scaling for plotting error circles at high declinations"""
            dec *= numpy.pi/180.
            radius *= numpy.pi/180.
            return numpy.arccos(numpy.cos(radius)/(numpy.cos(dec)**2) - numpy.tan(dec)**2) * 180./numpy.pi
    
        plot_radius_50 = error_circle_radius(extra_dec, extra_radius)

        dist = angular_distance(minRA, minDec, extra_ra * numpy.pi/180., extra_dec * numpy.pi/180.)
        print("Millipede best fit is", dist /(numpy.pi * extra_radius/(1.177 * 180.)), "sigma from reported best fit")

        plot_radius_90 = error_circle_radius(extra_dec, 2.55 * extra_radius)
        for i, plot_radius in enumerate([plot_radius_90, plot_radius_50]):
            print("Reported", [90, 50][i], "% error region (scaled)", plot_radius, "degrees")
            circle1 = matplotlib.pyplot.Circle((extra_ra *numpy.pi/180., extra_dec*numpy.pi/180.), plot_radius * numpy.pi/180.,
                                               color="g", alpha=[0.5, 1.0][i])
            ax.add_artist(circle1)
      
        ax.scatter(extra_ra*numpy.pi/180., extra_dec*numpy.pi/180., s=20, marker='o', color='green', label=r'Reported 50%/90%')




    ax.legend(loc='lower right', fontsize=8, scatterpoints=1, ncol=2)
    
    print("Contour Area (90%):", a, "degrees (cartesian)", a*numpy.cos(minDec)**2, "degrees (scaled)")
    x_width = 1.6 * numpy.sqrt(a)
    
    if numpy.isnan(x_width):
        x_width = 1.6*(max(CS.allsegs[i][0][:,0]) - min(CS.allsegs[i][0][:,0]))
    print(x_width)
    y_width = 0.5 * x_width

    lower_x = max(minRA  - x_width*numpy.pi/180., 0.)
    upper_x = min(minRA  + x_width*numpy.pi/180., 2 * numpy.pi)
    lower_y = max(minDec -y_width*numpy.pi/180., -numpy.pi/2.)
    upper_y = min(minDec + y_width*numpy.pi/180., numpy.pi/2.) 

    #ax.set_xlim( [ minRA  - 10.*numpy.pi/180. ,minRA  + 10.*numpy.pi/180.  ] )
    #ax.set_ylim( [ minDec - 5.*numpy.pi/180. ,minDec + 5.*numpy.pi/180.  ] )
    ax.set_xlim( [lower_x, upper_x])
    ax.set_ylim( [lower_y, upper_y])

    if systematics is True:
        x_width = 0.5 * 1.3 * (ra_p - ra_m)
        y_width = 0.5 * 1.3 * (dec_p - dec_m)
        
        y_width = numpy.radians(1.0)

        if x_width > 2 * y_width:
            y_width = 0.5 * x_width
        else:
            x_width = 2 * y_width

        print(x_width, y_width)
        mid_x = 0.5 * (ra_p + ra_m)
        mid_y = 0.5 * (dec_p + dec_m)
        lower_x = mid_x - x_width
        upper_x = mid_x + x_width
        lower_y = mid_y - y_width
        upper_y = mid_y + y_width
        print(lower_x, upper_x)

        ax.set_xlim( [lower_x, upper_x])
        ax.set_ylim( [lower_y, upper_y])
        ra_mask = numpy.logical_and(ra > lower_x, ra < upper_x)
        dec_mask = numpy.logical_and(dec > lower_y, dec < upper_y)
        cut_map = (((grid_map[dec_mask]).T)[ra_mask]).T
        path = event_id_string + ".gridmap.pkl"
        print("Saving Gridmap to", path, "(can be used for Fast Response Analysis)")
        with open(path, "wb") as f:
            Pickle.dump([cut_map, ra[ra_mask], dec[dec_mask]], f)


    ax.xaxis.set_major_formatter(DecFormatter())
    ax.yaxis.set_major_formatter(DecFormatter())

    factor = 0.25*(numpy.pi/180.)
    while (upper_x - lower_x)/factor > 6:
         factor *= 2.
    tick_label_grid = factor

    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=tick_label_grid))
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=tick_label_grid))
    
    ### PLOT 4FGL Sources
    print("Plot 4FGL Sources")
    with pyfits.open('/cvmfs/icecube.opensciencegrid.org/users/steinrob/reference_catalogues/gll_psc_v20.fit') as hdu:
        fgl = hdu[1]
        data_cat = fgl.data
    for jz in range(len(data_cat)):
        fname_i = data_cat['Source_Name'][jz]
        fra_i = data_cat['RAJ2000'][jz]
        fdec_i = data_cat['DEJ2000'][jz]

        fgl_coor_i = SkyCoord(ra = fra_i,dec = fdec_i,unit = 'deg', frame = 'fk5')
        ra_mask_i = numpy.logical_and(fgl_coor_i.ra.rad  > lower_x, fgl_coor_i.ra.rad < upper_x)
        dec_mask_i = numpy.logical_and(fgl_coor_i.dec.rad > lower_y, fgl_coor_i.dec.rad < upper_y)
        if ra_mask_i and dec_mask_i:
            ax.scatter(fgl_coor_i.ra.rad, fgl_coor_i.dec.rad, s=15, marker='o', color='burlywood')
            ax.text(fgl_coor_i.ra.rad,fgl_coor_i.dec.rad,str(fname_i),color = 'burlywood',fontsize=6)
        
        
    #################################

    if True:
        # colorbar
        cb = fig.colorbar(image, orientation='horizontal', shrink=.6, pad=0.13) #, ticks=[min_value, max_value_zoomed])
        cb.ax.xaxis.set_label_text(r"$-2 \Delta \ln (L)$")
        #cb.ax.xaxis.labelpad = -8
        # workaround for issue with viewers, see colorbar docstring
        cb.solids.set_edgecolor("face")

    ax.set_aspect('equal')

    ax.tick_params(axis='x', labelsize=10)
    ax.tick_params(axis='y', labelsize=10)

    ax.set_xlabel('right ascension')
    ax.set_ylabel('declination')

    # show the grid
    # ax.grid(True, color='w', alpha=0.5)
    ax.grid(True, color='k', alpha=0.5)

    from matplotlib import patheffects
    # Otherwise, add the path effects.
    effects = [patheffects.withStroke(linewidth=1.1, foreground='w')]
    for artist in ax.findobj(text.Text):
        artist.set_path_effects(effects)

    # remove white space around figure
    spacing = 0.01
    fig.subplots_adjust(bottom=spacing, top=0.92-spacing, left=spacing+0.1, right=1.-spacing)
    # fig.subplots_adjust(bottom=spacing, top=1.-spacing, left=spacing+0.1, right=1.-spacing)

    # set the title
    fig.suptitle(plot_title)

    print("saving: {0}...".format(plot_filename))
    ax.invert_xaxis()
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
    imgdata.truncate(0)
    del imgdata
    del data_cat, fgl

    #return plot_filename


def loop_over_plots(eventID, cache_dir, ra=numpy.nan, dec=numpy.nan, radius=numpy.nan, state_dict=None, log_func=None, upload_func=None, final_channels=None):
    from skymap_scanner.load_scan_state import load_cache_state
    # get the file stager instance

    if state_dict is None:
   
        stagers = dataio.get_stagers()

        eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=cache_dir)

    for i, syst in enumerate([True, False]):
        create_plot_zoomed(eventID, state_dict, syst, ra, dec, radius, log_func, upload_func, final_channels)
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

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    loop_over_plots(eventID, options.CACHEDIR, options.RA, options.DEC, options.RADIUS)

    # get the file stager instance
#    stagers = dataio.get_stagers()

#   eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=options.CACHEDIR)
#  for syst in [True, False]:
#     plot_png_buffer = create_plot_zoomed(eventID, state_dict, syst, options.RA, options.DEC, options.RADIUS)
# # we have a buffer containing a valid png file now, post it to Slack
# slack_tools.upload_file(plot_png_buffer, "skymap.png", "Skymap!")
