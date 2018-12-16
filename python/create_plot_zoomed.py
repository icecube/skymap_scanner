from __future__ import print_function
from __future__ import absolute_import

import io
import os
import numpy
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot
import healpy

from icecube import icetray, dataclasses, dataio

from icecube.skymap_scanner.utils import parse_event_id, get_event_mjd

# from . import slack_tools

from matplotlib.axes import Axes
from matplotlib import text
from matplotlib.ticker import Formatter, FixedFormatter, FixedLocator
from matplotlib.transforms import Transform, Affine2D
from matplotlib.projections import projection_registry
from matplotlib.projections.geo import MollweideAxes
import matplotlib.units as units
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

def create_plot(event_id_string, state_dict):
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

    plot_filename = "{0}.png".format(event_id_string)
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
    fig = matplotlib.pyplot.figure(figsize=[x_inches,y_inches])
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

    # # Wilk's
    # contour_levels = (numpy.array([1.39, 4.61, 11.83, 28.74])+min_value)[1:]
    # contour_labels = [r'50%', r'90%', r'3$\sigma$', r'5$\sigma$'][1:]
    # contour_colors=['0.5', 'k', 'r', 'g'][1:]
    CS = ax.contour(ra, dec, grid_map, levels=contour_levels, colors=contour_colors)
    ax.clabel(CS, inline=False, fontsize=12, fmt=dict(zip(contour_levels, contour_labels)))

    for i in range(len(contour_labels)):
        vs = CS.collections[i].get_paths()[0].vertices
        # Compute area enclosed by vertices.
        a = area(vs) # will be in square-radians
        a = a*(180.*180.)/(numpy.pi*numpy.pi) # convert to square-degrees

        CS.collections[i].set_label(contour_labels[i] + ' - area: {0:.2f}sqdeg'.format(a))

    # Add in additional plot point
    #pilot_ra = 158.99795262
    #plot_dec = 39.52818432
    #plot_ra = 26.533
    #plot_dec = 12.994
    #plot_radius = 0.06 * 1.177 / numpy.cos(plot_dec*numpy.pi/180.)
    #plot_radius = 2.55 / numpy.cos(plot_dec*numpy.pi/180.)
    plot_ra = 323.383
    plot_dec = 49.410
    plot_radius = 2.9 / numpy.cos(plot_dec*numpy.pi/180.)
    print("Plot radius", plot_radius, "degrees")
    ax.scatter(minRA, minDec, s=20, marker='s', color='black', label=r'scan best-fit', zorder=2)

    circle1 = matplotlib.pyplot.Circle((plot_ra *numpy.pi/180., plot_dec*numpy.pi/180.), plot_radius * numpy.pi/180., color='green', label=r'50% Parabaloid')
    ax.add_artist(circle1)
    # show GCN position
    #ax.scatter(98.3268*numpy.pi/180., -14.4861*numpy.pi/180., s=20, marker='s', color='burlywood', label='GCN Tue 21 Mar 17 07:32:58 UT')
    #ax.scatter(221.6750*numpy.pi/180., -26.0359*numpy.pi/180., s=20, marker='s', color='burlywood', label='GCN Sat 06 May 17 13:01:20 UT')
    # ax.scatter(77.2853*numpy.pi/180., 5.7517*numpy.pi/180., s=20, marker='s', color='burlywood', label='GCN Fri 22 Sep 17 20:55:13 UT')

    #ax.scatter(98.165*numpy.pi/180., -15.204*numpy.pi/180., s=20, marker='s', color='green', label='splineMPE fit')

    # ax.scatter(77.3581850*numpy.pi/180., 5.6931481*numpy.pi/180., s=20, marker='x', color='r', label='TXS 0506+056')


    # # show GCN position
    # ax.scatter(0.8003, 0.2755, s=20, marker='s', color='burlywood', label='GCN alert position')

    # for Pan-Starrs
    #show best-fit position
    #ax.scatter(minRA, minDec, s=20, marker='s', color='black', label=r'scan best-fit')
    ax.scatter(plot_ra*numpy.pi/180., plot_dec*numpy.pi/180., s=20, marker='o', color='green', label=r'Reported 90% Containment')
    
    # # show supernova position
    # ax.scatter(240.328*numpy.pi/180., 9.865*numpy.pi/180., s=100, marker='*', color='burlywood', label='SN PS16cgx')

    # 90%:
    # min  RA: 46.58 -1.00 +1.10 deg
    # min dec: 14.98 -0.80 +1.05 deg
    #
    # 50%:
    # min  RA: 46.58 -0.50 +0.55 deg
    # min dec: 14.98 -0.40 +0.45 deg


    # # 90%
    #ax.errorbar([minRA], [minDec],
    ax.errorbar([77.43*numpy.pi/180.], [5.72*numpy.pi/180.],
     xerr=[[0.8*numpy.pi/180.],[1.3*numpy.pi/180.]], # RA
     yerr=[[0.4*numpy.pi/180.],[0.7*numpy.pi/180.]], # Dec
     color='g', fmt='--o')

    ## 50 %
    #ax.errorbar([minRA], [minDec],
    # xerr=[[0.5*numpy.pi/180.],[0.55*numpy.pi/180.]], # RA
    # yerr=[[0.4*numpy.pi/180.],[0.45*numpy.pi/180.]], # Dec
    # color='k', fmt='--o')

    ## # 90%
    #ax.errorbar([77.68*numpy.pi/180.], [5.87*numpy.pi/180.],
    # xerr=[[1.05*numpy.pi/180.],[1.05*numpy.pi/180.]], # RA
    # yerr=[[0.55*numpy.pi/180.],[0.55*numpy.pi/180.]], # Dec
    # color='b', fmt='--o')



    ax.legend(loc='lower right', fontsize=8, scatterpoints=1, ncol=2)

    # # graticule
    # ax.set_longitude_grid(30)
    # ax.set_latitude_grid(30)

    # ax.set_xlim( [ minRA  - 30.*numpy.pi/180. ,minRA  + 30.*numpy.pi/180.  ] )
    # ax.set_ylim( [ minDec - 15.*numpy.pi/180. ,minDec + 15.*numpy.pi/180.  ] )
    
    print("Contour Area (90%):", a, "degrees")
    x_width = 1.6 * numpy.sqrt(a)
    y_width = 0.5 * x_width

    #ax.set_xlim( [ minRA  - 10.*numpy.pi/180. ,minRA  + 10.*numpy.pi/180.  ] )
    #ax.set_ylim( [ minDec - 5.*numpy.pi/180. ,minDec + 5.*numpy.pi/180.  ] )
    ax.set_xlim( [ minRA  - x_width*numpy.pi/180. ,minRA  + x_width*numpy.pi/180.  ] )
    ax.set_ylim( [ minDec -y_width*numpy.pi/180. ,minDec + y_width*numpy.pi/180.  ] )


    # ax.xaxis.set_major_formatter(RaFormatter())
    ax.xaxis.set_major_formatter(DecFormatter())
    ax.yaxis.set_major_formatter(DecFormatter())

    factor = 0.25
    while x_width/factor > 6:
         factor *= 2.
    tick_label_grid = factor * (numpy.pi/180.)

    #ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=2.0*(numpy.pi/180.)))
    #ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=2.0*(numpy.pi/180.)))
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=tick_label_grid))
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=tick_label_grid))

    # ax.xaxis.set_ticks(numpy.arange(0., 2.*numpy.pi, 1000))

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

    fig.savefig(event_id_string + ".plot_zoomed.pdf", dpi=dpi, transparent=True)

    # # use io.BytesIO to save this into a memory buffer
    # imgdata = io.BytesIO()
    # fig.savefig(imgdata, format='png', dpi=dpi, transparent=True)
    # imgdata.seek(0)

    print("done.")

    # return imgdata


if __name__ == "__main__":
    from optparse import OptionParser
    from icecube.skymap_scanner.load_scan_state import load_cache_state

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    #parser.add_option("--ra", action="store", type="float",
    #    default=np.nan, help="Right Ascension in degrees")
    #parser.add_option("--dec", action="store", type="float",
    #    default=np.nan, help="Declination in degrees")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event ID")
    eventID = args[0]

    # get the file stager instance
    stagers = dataio.get_stagers()

    eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=options.CACHEDIR)
    plot_png_buffer = create_plot(eventID, state_dict)

    # # we have a buffer containing a valid png file now, post it to Slack
    # slack_tools.upload_file(plot_png_buffer, "skymap.png", "Skymap!")
