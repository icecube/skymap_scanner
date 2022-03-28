# fmt: off
# isort: skip_file

import os
import numpy as np

from I3Tray import I3Units
from icecube import icetray, dataclasses, dataio
from icecube import gulliver, millipede

from skymap_scanner import load_cache_state
import matplotlib.pyplot as plt

# import os
# import math
# import numpy as np
# from I3Tray import *
# from icecube import icetray, dataclasses, phys_services, photonics_service, dataio, simclasses
# from icecube.icetray import I3Units
# import tables
# import pandas as pd
# from cubicle import hdfweights
# import numpy as np
# import pylab as p
# import matplotlib.pyplot as plt


def extract_cascade_info(eventID, cache_dir):

    # get the file stager instance
    stagers = dataio.get_stagers()

    # do the work
    eventID, state_dict = load_cache_state(eventID, filestager=stagers,
                                           cache_dir=cache_dir)

    # print "got:", eventID, state_dict

    best_llh = None
    best_energy = None
    best_pix = None
    best_nside = None
    best_data = None
    for nside in list(state_dict['nsides'].keys()):
        for pixel, pixel_data in list(state_dict["nsides"][nside].items()):
            llh = pixel_data['llh']
            energy = pixel_data['recoLossesInside']
            if best_llh is None or llh < best_llh:
                best_llh = llh
                best_pix = pixel
                best_nside = nside
                best_energy = energy
                best_data = pixel_data

    print(("best-fit pixel: nside =", best_nside, ", best_pix =", best_pix, ", best_llh =", best_llh, ", best_energy =", best_energy / I3Units.TeV, "TeV"))

    gcdfilehandle = state_dict['baseline_GCD_file']

    if not os.path.isfile(gcdfilehandle):
        gcdfilehandle = "/cvmfs/icecube.opensciencegrid.org/users/steinrob/" \
                        "GCD/PoleBaseGCDs/baseline_gcd_131577.i3"


    def center(x):
        return 0.5*(x[:-1] + x[1:])

    # Binning

    loge = np.arange(3.5, 8.5, 0.5) + 0.25
    loge_centers = 10**center(loge)
    ctbins = np.linspace(-1, 1, 11)
    ct_centers = 0.5*(ctbins[1:] + ctbins[:-1])

    distbins = np.linspace(0, 25000, 25000)
    dist_centers = 0.5*(distbins[1:] + distbins[:-1])

    distlog = np.logspace(0, 7, 100)
    distlog_ctr = np.sqrt(distlog[:-1] * distlog[1:])

    gcdfile = dataio.I3File(str(gcdfilehandle))
    frame = gcdfile.pop_frame()
    while not 'I3Geometry' in frame:
       frame = gcdfile.pop_frame()
    geometry = frame['I3Geometry'].omgeo
    gcdfile.close()

#
    # DOM positions
    dom_x = list()
    dom_y = list()
    dom_z = list()
    for omkey, omgeo in geometry:
        dom_x.append(geometry[omkey].position.x)
        dom_y.append(geometry[omkey].position.y)
        dom_z.append(geometry[omkey].position.z)

    frame_in = best_data["frame"]
    eventHeader = frame_in['I3EventHeader']

    spline = frame_in["MillipedeStarting2ndPass"]
    millipede = frame_in['MillipedeStarting2ndPassParams']

    cscd_x = []
    cscd_y = []
    cscd_z = []
    cscd_e = []
    cscd_t = []
    for cscd in millipede:
        cscd_x.append(cscd.pos.x)
        cscd_y.append(cscd.pos.y)
        cscd_z.append(cscd.pos.z)
        cscd_e.append(cscd.energy)
        cscd_t.append(cscd.time/1e3)


    import matplotlib.cm as cm

    dim_pairs = [
        ("xy", dom_x, dom_y, cscd_x, cscd_y),
        ("xz", dom_x, dom_z, cscd_x, cscd_z),
        ("yz", dom_y, dom_z, cscd_y, cscd_z),
    ]

    for (ab, dom_a, dom_b, cscd_a, cscd_b) in dim_pairs:

        fig = plt.figure(figsize=(12, 10))

        detector = plt.scatter(dom_a, dom_b, s=20, marker='o', color='C7',
                               alpha=0.5, edgecolor='none')

        colour_scale = 1.e4 * np.array(cscd_e)/max(cscd_e)

        mill = plt.scatter(cscd_a, cscd_b, s=colour_scale,
                           c=(np.array(cscd_t) - min(cscd_t)),
                           cmap=cm.viridis_r, alpha=0.6, label=None)

        # cb = plt.colorbar(label='Time [ns]', fontsize=20)
        cb = plt.colorbar(aspect=50)
        cb.set_label(label='Time [$\mu$s]', fontsize=20)
        axcb = cb.ax
        plt.setp(axcb.get_yticklabels(), size=18)

        size = 1
        plot1 = plt.scatter(cscd_a, cscd_b, s=0.001, color='C0')

        plt.xlabel(ab[0] + ' [m]', fontsize=18)
        plt.ylabel(ab[1] + ' [m]', fontsize=18)

        xmin = -750
        xmax = +750
        ymin = -750
        ymax = +750
        plt.xlim(xmin, xmax)
        plt.ylim(ymin, ymax)
        # # print xmin, xmax

        ax = plt.gca()
        plt.setp(ax.get_xticklabels(), size=18)
        plt.setp(ax.get_yticklabels(), size=18)
        plt.tight_layout()
        plt.grid(0)

        savename = eventID + ".millipede_" + ab + ".pdf"
        print(("Saving to", savename))
        plt.savefig(savename)
        plt.close()

    cscd_x = []
    cscd_y = []
    cscd_z = []
    cscd_e = []
    cscd_t = []
    for cscd in millipede:
        cscd_x.append(cscd.pos.x)
        cscd_y.append(cscd.pos.y)
        cscd_z.append(cscd.pos.z)
        cscd_e.append(cscd.energy)
        cscd_t.append(cscd.time/1e3)

    cscd_in_detector = []
    index_in_detector = []
    for n, cscd in enumerate(millipede):
        if cscd.pos.z > dom_z[-1] and cscd.pos.z < dom_z[4037]:
            if cscd.pos.y > dom_y[1] and cscd.pos.y < dom_y[4933]:
                cscd_in_detector.append(cscd)
                index_in_detector.append(n)

    # fig = plt.figure(figsize = (10,7))
    # plt.hist(cscd_e, bins=np.linspace(min(cscd_e), max(cscd_e), 1000),
    #          histtype='step', lw=3)
    # plt.xscale(u'log')
    # plt.yscale(u'log')

    print(("Number of non-zero cascaes:", np.sum(np.array(cscd_e) > 0.)))

    # fig = plt.figure(figsize=(12, 10))
    # # ax = fig.add_subplot(111)
    #
    # detector = plt.scatter(dom_y, dom_z,
    #                        s=20,
    #                        marker='o',
    #                        color='C7',
    #                        alpha=0.5,
    #                        edgecolor='none')
    #
    # mill = plt.scatter(millipede[index_in_detector[0]].pos.y,
    #                    millipede[index_in_detector[0]].pos.z,
    #                    s=100, c=millipede[56].time,
    #                    cmap=cm.viridis, alpha=0.6,
    #                    label=None)
    #
    # # cb = plt.colorbar(label='Time [ns]', fontsize=20)
    # cb = plt.colorbar(aspect=50)
    # cb.set_label(label='Time [$\mu$s]', fontsize=20)
    # axcb = cb.ax
    # plt.setp(axcb.get_yticklabels(), size=18)
    #
    # # track
    # plt.scatter(spline.pos.y, spline.pos.z, marker='*', s=100)
    # plt.plot([spline.pos.y - spline.dir.y * 5000,
    #           spline.pos.y + spline.dir.y * 5000],
    #          [spline.pos.z - spline.dir.z * 5000,
    #           spline.pos.z + spline.dir.z * 5000])
    #
    # size = 1
    # plot1 = plt.scatter(millipede[56].pos.y, millipede[56].pos.z,
    #                     s=0.001, label='Millipede Cascades',
    #                     color=cm.viridis(0), alpha=0.6)
    #
    # plt.legend(loc="upper left", markerscale=300, scatterpoints=3, fontsize=20,
    #            prop={'size': 20})
    #
    # plt.xlabel('Y [m]', fontdict=font)
    # plt.ylabel('Z [m]', fontdict=font)
    #
    # xmin = -750
    # xmax = +750
    # ymin = -750
    # ymax = +750
    # plt.xlim(xmin, xmax)
    # plt.ylim(ymin, ymax)
    # # # print xmin, xmax
    #
    # ax = plt.gca()
    # plt.setp(ax.get_xticklabels(), size=18)
    # plt.setp(ax.get_yticklabels(), size=18)
    #
    # # plt.title('Event number: %s, MC energy: %2.0f GeV,  \nalpha_um = %2.3f deg,alpha_ssmpe (Millipede) = %2.3f deg, alpha_ssmpe (UM) = %2.3f deg'
    # #           %(df_millipede_cscd_ev['eventID2'][0], df_millipede_cscd_ev['energy'][0], alpha_um, alpha_ssmpe_mil, alpha_ssmpe_um), fontsize=15, y=1.02)
    # plt.tight_layout()
    # plt.grid(0)
    # savename = eventID + ".millipede_check_intersection.pdf"
    # print "Saving to", savename
    # plt.savefig(savename)
    # plt.close()

    dist_from_cscd = []
    first_cscd = millipede[index_in_detector[0]]

    for count, cas in enumerate(millipede):
        dist = np.sqrt((first_cscd.pos.x - cas.pos.x) ** 2 +
                       (first_cscd.pos.y - cas.pos.y) ** 2 +
                       (first_cscd.pos.z - cas.pos.z) ** 2)
        dist_from_cscd.append(dist)

    fig = plt.figure()

    plt.hist(dist_from_cscd, weights=cscd_e, bins=25, histtype='step')
    plt.yscale('log')
    plt.ylim(1e-1, 10*max(cscd_e))

    plt.ylabel('Energy [GeV]')
    plt.xlabel('Distance from first cascade [m]')

    plt.tight_layout()
    plt.grid(0)
    savename = eventID + ".millipede_energy_histogram.pdf"
    print(("Saving to", savename))
    plt.savefig(savename)

    fig = plt.figure()
    weights = np.array(cscd_e)/np.sum(cscd_e)

    plt.hist(dist_from_cscd, weights=weights, bins=1000, histtype='step',
             cumulative=True)
    # plt.step(dist_from_cscd, weights)
    # plt.yscale(u'log')
    plt.ylim(0., 1.)

    plt.ylabel('Fraction of Energy')
    plt.xlabel('Distance from first cascade [m]')
    plt.tight_layout()
    plt.grid(0)
    savename = eventID + ".millipede_cumulative_energy_histogram.pdf"
    print(("Saving to", savename))
    plt.savefig(savename)

    max_cscd_fraction = max(cscd_e)/np.sum(cscd_e)

    print(("Fraction of energy in largest cascade:", max_cscd_fraction))
    return max_cscd_fraction


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
                      default="./cache/", dest="CACHEDIR",
                      help="The cache directory to use")

    # get parsed args
    (options, args) = parser.parse_args()

    if len(args) == 1:
        eventID = args[0]

        extract_cascade_info(eventID, options.CACHEDIR)

    else:

        fracs = []

        for eventID in os.listdir(options.CACHEDIR):
            try:
                fracs.append(extract_cascade_info(eventID, options.CACHEDIR))
            except:
                pass

        print(("Final Fractions", fracs))
