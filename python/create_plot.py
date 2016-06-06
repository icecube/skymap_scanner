import os
import numpy
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot
import healpy


from icecube import icetray, dataio

from utils import parse_event_id

# from choose_new_pixels_to_scan import find_pixels_to_refine

def create_plot(event_id_string, state_dict):
    y_inches = 3.85
    x_inches = 6.
    dpi = 900.
    xsize = x_inches*900.

    lonra=[-10.,10.]
    latra=[-10.,10.]

    if "nsides" not in state_dict:
        raise RuntimeError("\"nsides\" not in dictionary..")

    run_id, event_id, event_type = parse_event_id(event_id_string)

    plot_title = "Run: {0} Event {1}: Type: {2}".format(run_id, event_id, event_type)

    plot_filename = "{0}.pdf".format(event_id_string)
    print "saving plot to {0}".format(plot_filename)

    nsides = state_dict["nsides"].keys()
    print "available nsides: {0}".format(nsides)

    maps = []
    min_value = numpy.nan
    max_value = numpy.nan
    minAzimuth=0.
    minZenith=0.

    # now plot maps above each other
    for nside in sorted(nsides):
        print "constructing map for nside {0}...".format(nside)
        this_map = numpy.ones(healpy.nside2npix(nside))*numpy.inf
        for pixel, pixel_data in state_dict["nsides"][nside].iteritems():
            value = pixel_data['llh']
            if numpy.isfinite(value):
                if numpy.isnan(min_value) or value < min_value:
                    minZenith, minAzimuth = healpy.pix2ang(nside, pixel)
                    min_value = value
                if numpy.isnan(max_value) or value > max_value:
                    max_value = value
            this_map[pixel] = value
        print "done with map for nside {0}...".format(nside)

        maps.append(this_map)

    max_value_zoomed = min_value+7.

    print "preparing plot: {0}...".format(plot_filename)

    # prepare the figure canvas
    fig = matplotlib.pyplot.figure(figsize=[x_inches+y_inches,y_inches])
    # rect = (left, bottom, width, height)
    ax = healpy.projaxes.HpxMollweideAxes(fig,(0.,0., x_inches/(x_inches+y_inches) ,1.))
    fig.add_axes(ax)
    bx = healpy.projaxes.HpxCartesianAxes(
        fig,
        (x_inches/(x_inches+y_inches), 0., y_inches/(x_inches+y_inches) ,1.),
        rot=(minAzimuth*180./numpy.pi,90.-minZenith*180/numpy.pi,0.)
    )
    fig.add_axes(bx)

    # display a map with all pixels masked below all others
    this_map = healpy.ma(numpy.ones(healpy.nside2npix(2))*0.5)
    cmap = matplotlib.cm.gray
    cmap.set_under(alpha=0.) # make underflows transparent
    ax.projmap(this_map, vmin=0.,vmax=1.,xsize=xsize,cmap=cmap)
    bx.projmap(this_map, vmin=0.,vmax=1.,xsize=xsize,cmap=cmap, lonra=lonra, latra=latra)

    # the color map to use
    cmap = matplotlib.cm.cubehelix_r
    cmap.set_under(alpha=0.) # make underflows transparent
    cmap.set_over(alpha=0.)  # make underflows transparent
    cmap.set_bad(alpha=1., color=(1.,0.,0.)) # make NaNs bright red

    print "plotting: {0}...".format(plot_filename)

    # plot the images
    img = None
    for this_map in maps:
        # create main image
        img = ax.projmap(this_map, xsize=xsize, vmin=min_value, vmax=max_value, cmap=cmap)
        img = bx.projmap(this_map, xsize=xsize, vmin=min_value, vmax=max_value_zoomed, cmap=cmap, lonra=lonra, latra=latra)

    # create colorbars
    im = ax.get_images()[1]
    b = im.norm.inverse(numpy.linspace(0,1,im.cmap.N+1))
    v = numpy.linspace(im.norm.vmin,im.norm.vmax,im.cmap.N)
    cb=fig.colorbar(im,ax=ax,
                    orientation='horizontal',
                    shrink=0.5,aspect=25,ticks=healpy.projaxes.BoundaryLocator(),
                    pad=0.05,fraction=0.1,boundaries=b,values=v,
                    format='%g')

    # create colorbars
    im = bx.get_images()[1]
    b = im.norm.inverse(numpy.linspace(0,1,im.cmap.N+1))
    v = numpy.linspace(im.norm.vmin,im.norm.vmax,im.cmap.N)
    cb=fig.colorbar(im,ax=bx,
                    orientation='horizontal',
                    shrink=0.5,aspect=25,ticks=healpy.projaxes.BoundaryLocator(),
                    pad=0.05,fraction=0.1,boundaries=b,values=v,
                    format='%g')

    # set the title
    ax.set_title(plot_title)

    # graticules
    ax.graticule()
    bx.graticule()

    print "saving: {0}...".format(plot_filename)

    fig.savefig(plot_filename, dpi=dpi, transparent=True)

    print "done."


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

    eventID, state_dict = load_cache_state(eventID, cache_dir=options.CACHEDIR)
    create_plot(eventID, state_dict)
