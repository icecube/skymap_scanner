import numpy as np
import matplotlib.patheffects as path_effects
from matplotlib.axes import Axes
from matplotlib.ticker import Formatter, FixedFormatter, FixedLocator
from matplotlib.transforms import Transform, Affine2D
from matplotlib.projections import projection_registry
from matplotlib.projections.geo import MollweideAxes
import matplotlib
matplotlib.use('agg')
from matplotlib import pyplot as plt
import healpy
import astropy.io.fits as pyfits

def format_fits_header(event_id_tuple, mjd, ra, dec, uncertainty):
    '''Prepare some of the relevant event information for 
    a fits file header'''
    run_id, event_id, event_type = event_id_tuple

    header = [
        ('RUNID', run_id), 
        ('EVENTID', event_id),
        ('SENDER', 'IceCube Collaboration'),
        ('EventMJD', mjd),
        ('I3TYPE', '%s'%event_type,'Alert Type'),
        ('RA', np.round(ra,2),'Degree'),
        ('DEC', np.round(dec,2),'Degree'),
        ('RA_ERR_PLUS', np.round(uncertainty[0][1],2),
            '90% containment error high'),
        ('RA_ERR_MINUS', np.round(np.abs(uncertainty[0][0]),2),
            '90% containment error low'),
        ('DEC_ERR_PLUS', np.round(uncertainty[1][1],2),
            '90% containment error high'),
        ('DEC_ERR_MINUS', np.round(np.abs(uncertainty[1][0]),2),
            '90% containment error low'),
        ('COMMENTS', '50%(90%) uncertainty location' \
            + ' => Change in 2LLH based on Wilks theorem'),
        ('NOTE', 'Please ignore pixels with infinite or NaN values.' \
            + ' They are rare cases of the minimizer failing to converge')
        ]
    return header


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
        min_lon = np.round(lon_offset/2.)*2. - 2
        max_lon = lon_offset+lonra[1]-lonra[0] + 2
        lons = np.arange(min_lon, max_lon, 2)
        
        min_lat = np.round(lat_offset/2.)*2. - 2
        max_lat = lat_offset+latra[1]-latra[0] + 2
        lats = np.arange(min_lat, max_lat, 2)

        lon_set = []
        for lon in lons:
            if lon > lower_lon and lon < upper_lon:
                lon_set.append(lon)

        lat_set = []
        for lat in lats:
            if lat > lower_lat and lat < upper_lat:
                lat_set.append(lat)

        lons = np.array(lon_set)
        lats = np.array(lat_set)
        lat_offset = rot[1]+latra[1] + 0.05*(latra[1]-latra[0])
    else:
        lon_offset = -180
        lat_offset = 0

        # lonlat coordinates for labels
        lons = np.arange(-150, 181, 30)
        lats = np.arange(-90, 91, 30)

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
    hdu = pyfits.open('/cvmfs/icecube.opensciencegrid.org/users/steinrob/reference_catalogues/Fermi_4FGL_v18.fit')
    fgl = hdu[1]
    pe = [path_effects.Stroke(linewidth=0.5, foreground=cmap(0.0)),
        path_effects.Normal()]

    fname_i = np.array(fgl.data['Source_Name'])
    fra_i = np.array(fgl.data['RAJ2000'])*np.pi/180.
    fdec_i = np.array(fgl.data['DEJ2000'])*np.pi/180.
    fgl_mask = np.logical_and(np.logical_and(fra_i > lower_ra, fra_i < upper_ra), np.logical_and(fdec_i > lower_dec, fdec_i < upper_dec))
    flon_i = fra_i
    flat_i = -fdec_i

    def color_filter(lon, lat):
        vals = healpy.get_interp_val(master_map, lon, lat, lonlat=True)
        vals = (healpy.get_interp_val(master_map, lon, lat, lonlat=True) - cmap_min)/(cmap_max-cmap_min)
        vals = np.where(vals < 0.0, 0.0, vals)
        vals = np.where(vals > 1.0, 1.0, vals)
        vals = np.round(1.0-vals)
        return vals

    healpy.projscatter(
        flon_i[fgl_mask]*180./np.pi,
        flat_i[fgl_mask]*180./np.pi,
        lonlat=True,
        c=cmap(color_filter(flon_i[fgl_mask]*180./np.pi, flat_i[fgl_mask]*180./np.pi)),
        marker='o',
        s=10)
    for i in range(len(fgl_mask)):
        if not fgl_mask[i]:
            continue
        healpy.projtext(flon_i[i]*180./np.pi,
                flat_i[i]*180./np.pi,
                fname_i[i],
                lonlat=True,
                color = cmap(1.0),
                fontsize=6,
                path_effects=pe)
    del fgl


##
# Mollweide axes with phi axis flipped and in hours from 24 to 0 instead of
#         in degrees from -180 to 180.
class RaFormatter(Formatter):
    def __init__(self):
        pass

    def __call__(self, x, pos=None):
        hours = (x / np.pi) * 12.
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
        degrees = (x / np.pi) * 180.
        return r"$%0.1f^\circ$" % (degrees)
        # return r"%0.0f$^\circ$" % (degrees)

class AstroMollweideAxes(MollweideAxes):
    name = 'astro mollweide'

    def cla(self):
        super(AstroMollweideAxes, self).cla()
        self.set_xlim(0, 2*np.pi)

    def set_xlim(self, *args, **kwargs):
        Axes.set_xlim(self, 0., 2*np.pi)
        Axes.set_ylim(self, -np.pi / 2.0, np.pi / 2.0)

    def _get_core_transform(self, resolution):
        return Affine2D().translate(-np.pi, 0.) + super(AstroMollweideAxes, self)._get_core_transform(resolution)

    class RaFormatter(Formatter):
        # Copied from matplotlib.geo.GeoAxes.ThetaFormatter and modified
        def __init__(self, round_to=1.0):
            self._round_to = round_to

        def __call__(self, x, pos=None):
            hours = (x / np.pi) * 12.
            hours = round(15 * hours / self._round_to) * self._round_to / 15
            return r"%0.0f$^\mathrm{h}$" % hours

    def set_longitude_grid(self, degrees):
        # Copied from matplotlib.geo.GeoAxes.set_longitude_grid and modified
        number = (360 // degrees) + 1
        self.xaxis.set_major_locator(
            FixedLocator(
                np.linspace(0, 2*np.pi, number, True)[1:-1]))
        self._longitude_degrees = degrees
        self.xaxis.set_major_formatter(self.RaFormatter(degrees))

    def _set_lim_and_transforms(self):
        # Copied from matplotlib.geo.GeoAxes._set_lim_and_transforms and modified
        super(AstroMollweideAxes, self)._set_lim_and_transforms()

        # This is the transform for latitude ticks.
        yaxis_stretch = Affine2D().scale(np.pi * 2.0, 1.0)
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
        _, yscale = transform.transform_point((0, np.pi / 2.0))
        return Affine2D() \
            .scale(0.5 / xscale, 0.5 / yscale) \
            .translate(0.5, 0.5)

projection_registry.register(AstroMollweideAxes)
