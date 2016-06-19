import io
import os
import numpy
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot
import healpy

from icecube import icetray, dataclasses, dataio

from utils import parse_event_id, get_event_mjd

import slack_tools

from matplotlib.axes import Axes
from matplotlib import text
from matplotlib.ticker import Formatter, FixedFormatter, FixedLocator
from matplotlib.transforms import Transform, Affine2D
from matplotlib.projections import projection_registry
from matplotlib.projections.geo import MollweideAxes
##
# Mollweide axes with phi axis flipped and in hours from 24 to 0 instead of
#         in degrees from -180 to 180.
class AstroMollweideAxes(MollweideAxes):

    name = 'astro mollweide'

    def cla(self):
        super(AstroMollweideAxes, self).cla()
        self.set_xlim(0, 2*numpy.pi)

    def set_xlim(self, *args, **kwargs):
        Axes.set_xlim(self, 0., 2*numpy.pi)
        Axes.set_ylim(self, -numpy.pi / 2.0, numpy.pi / 2.0)

    def _get_core_transform(self, resolution):
        return Affine2D().translate(-numpy.pi, 0.) + super(AstroMollweideAxes, self)._get_core_transform(resolution)

    class RaFormatter(Formatter):
        # Copied from matplotlib.geo.GeoAxes.ThetaFormatter and modified
        def __init__(self, round_to=1.0):
            self._round_to = round_to

        def __call__(self, x, pos=None):
            hours = (x / numpy.pi) * 12.
            hours = round(15 * hours / self._round_to) * self._round_to / 15
            return r"%0.0f$^\mathrm{h}$" % hours

    def set_longitude_grid(self, degrees):
        # Copied from matplotlib.geo.GeoAxes.set_longitude_grid and modified
        number = (360.0 / degrees) + 1
        self.xaxis.set_major_locator(
            FixedLocator(
                numpy.linspace(0, 2*numpy.pi, number, True)[1:-1]))
        self._longitude_degrees = degrees
        self.xaxis.set_major_formatter(self.RaFormatter(degrees))

    def _set_lim_and_transforms(self):
        # Copied from matplotlib.geo.GeoAxes._set_lim_and_transforms and modified
        super(AstroMollweideAxes, self)._set_lim_and_transforms()

        # This is the transform for latitude ticks.
        yaxis_stretch = Affine2D().scale(numpy.pi * 2.0, 1.0)
        yaxis_space = Affine2D().scale(-1.0, 1.1)
        self._yaxis_transform = \
            yaxis_stretch + \
            self.transData
        yaxis_text_base = \
            yaxis_stretch + \
            self.transProjection + \
            (yaxis_space + \
             self.transAffine + \
             self.transAxes)
        self._yaxis_text1_transform = \
            yaxis_text_base + \
            Affine2D().translate(-8.0, 0.0)
        self._yaxis_text2_transform = \
            yaxis_text_base + \
            Affine2D().translate(8.0, 0.0)

    def _get_affine_transform(self):
        transform = self._get_core_transform(1)
        xscale, _ = transform.transform_point((0, 0))
        _, yscale = transform.transform_point((0, numpy.pi / 2.0))
        return Affine2D() \
            .scale(0.5 / xscale, 0.5 / yscale) \
            .translate(0.5, 0.5)

projection_registry.register(AstroMollweideAxes)

def create_plot(event_id_string, state_dict):
    y_inches = 3.85
    x_inches = 6.
    dpi = 150.
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
    print "saving plot to {0}".format(plot_filename)

    nsides = state_dict["nsides"].keys()
    print "available nsides: {0}".format(nsides)

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
        print "constructing map for nside {0}...".format(nside)
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
            this_map[pixel] = value
        
        if grid_map is None:
            grid_map = this_map[grid_pix]
        else:
            grid_map = numpy.where( numpy.isfinite(this_map[grid_pix]), this_map[grid_pix], grid_map)

        del this_map

        print "done with map for nside {0}...".format(nside)
    
    # clean up
    del grid_pix

    grid_map = numpy.ma.masked_invalid(grid_map)

    max_value_zoomed = min_value+7.

    print "preparing plot: {0}...".format(plot_filename)

    # the color map to use
    cmap = matplotlib.cm.cubehelix_r
    cmap.set_under(alpha=0.) # make underflows transparent
    cmap.set_over(alpha=0.)  # make underflows transparent
    cmap.set_bad(alpha=1., color=(1.,0.,0.)) # make NaNs bright red

    # prepare the figure canvas
    fig = matplotlib.pyplot.figure(figsize=[x_inches,y_inches])
    ax = fig.add_subplot(111,projection='astro mollweide')
    
    # rasterized makes the map bitmap while the labels remain vectorial
    # flip longitude to the astro convention
    image = ax.pcolormesh(ra, dec, grid_map, vmin=min_value, vmax=max_value, rasterized=True, cmap=cmap)
    # ax.set_xlim(numpy.pi, -numpy.pi)

    contour_levels = (numpy.array([1.39, 4.61, 11.83, 28.74])+min_value)[1:]
    contour_labels = [r'50%', r'90%', r'3$\sigma$', r'5$\sigma$'][1:]
    contour_colors=['0.5', 'k', 'r', 'g'][1:]
    CS = ax.contour(ra, dec, grid_map, levels=contour_levels, colors=contour_colors)
    ax.clabel(CS, inline=False, fontsize=4, fmt=dict(zip(contour_levels, contour_labels)))

    # graticule
    ax.set_longitude_grid(30)
    ax.set_latitude_grid(30)
    
    # colorbar
    cb = fig.colorbar(image, orientation='horizontal', shrink=.6, pad=0.05, ticks=[min_value, max_value])
    cb.ax.xaxis.set_label_text("-ln(L)")
    cb.ax.xaxis.labelpad = -8
    # workaround for issue with viewers, see colorbar docstring
    cb.solids.set_edgecolor("face")

    ax.tick_params(axis='x', labelsize=10)
    ax.tick_params(axis='y', labelsize=10)

    # show the grid
    ax.grid(True, color='w', alpha=0.5)

    from matplotlib import patheffects
    # Otherwise, add the path effects.
    effects = [patheffects.withStroke(linewidth=1.1, foreground='w')]
    for artist in ax.findobj(text.Text):
        artist.set_path_effects(effects)
            
    # remove white space around figure
    spacing = 0.01
    fig.subplots_adjust(bottom=spacing, top=1.-spacing, left=spacing+0.04, right=1.-spacing)
    
    # set the title
    fig.suptitle(plot_title)

    print "saving: {0}...".format(plot_filename)

    # fig.savefig(plot_filename, dpi=dpi, transparent=True)

    # use io.BytesIO to save this into a memory buffer
    imgdata = io.BytesIO()
    fig.savefig(imgdata, format='png', dpi=dpi, transparent=True)
    imgdata.seek(0)

    print "done."

    return imgdata


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

    # get the file stager instance
    stagers = dataio.get_stagers()

    eventID, state_dict = load_cache_state(eventID, filestager=stagers, cache_dir=options.CACHEDIR)
    plot_png_buffer = create_plot(eventID, state_dict)
    
    # we have a buffer containing a valid png file now, post it to Slack
    slack_tools.upload_file(plot_png_buffer, "skymap.png", "Skymap!")
