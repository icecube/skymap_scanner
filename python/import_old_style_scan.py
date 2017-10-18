import os
import numpy

from icecube import icetray, dataclasses, dataio
from icecube import gulliver, millipede

from utils import save_GCD_frame_packet_to_file, create_event_id
from extract_json_message import __extract_frame_packet

def import_old_style_scan(filename, filestager, cache_dir="./cache/", override_GCD_filename=None):
    old_style_i3f = dataio.I3File(filename, 'r')

    # read GCDQp
    GCDQp_packet = []
    GCDQp_packet.append(old_style_i3f.pop_frame())
    if GCDQp_packet[-1].Stop == icetray.I3Frame.TrayInfo:
        GCDQp_packet[-1] = old_style_i3f.pop_frame()
    if GCDQp_packet[-1].Stop != icetray.I3Frame.Geometry:
        raise RuntimeError("No G-frame in input file")
    GCDQp_packet.append(old_style_i3f.pop_frame())
    if GCDQp_packet[-1].Stop != icetray.I3Frame.Calibration:
        raise RuntimeError("No C-frame in input file")
    GCDQp_packet.append(old_style_i3f.pop_frame())
    if GCDQp_packet[-1].Stop != icetray.I3Frame.DetectorStatus:
        raise RuntimeError("No D-frame in input file")
    GCDQp_packet.append(old_style_i3f.pop_frame())
    if GCDQp_packet[-1].Stop != icetray.I3Frame.DAQ:
        raise RuntimeError("No Q-frame in input file")
    GCDQp_packet.append(old_style_i3f.pop_frame())
    if GCDQp_packet[-1].Stop != icetray.I3Frame.Stream('p') and GCDQp_packet[-1].Stop != icetray.I3Frame.Physics:
        raise RuntimeError("No p-frame in input file")

    print "importing GCDQp..."
    this_event_cache_dir, event_id_string, scan_dict = __extract_frame_packet(GCDQp_packet, filestager, cache_dir=cache_dir, override_GCD_filename=override_GCD_filename, pulsesName="SplitInIcePulses")

    if "nsides" not in scan_dict: scan_dict["nsides"] = dict()

    print "importing P-frame scans..."
    while old_style_i3f.more():
        frame = old_style_i3f.pop_frame()

        if "SCAN_HealpixPixel" not in frame:
            raise RuntimeError("\"SCAN_HealpixPixel\" not in frame")
        if "SCAN_HealpixNSide" not in frame:
            raise RuntimeError("\"SCAN_HealpixNSide\" not in frame")
        nside = frame["SCAN_HealpixNSide"].value
        pixel = frame["SCAN_HealpixPixel"].value

        if nside not in scan_dict["nsides"]: scan_dict["nsides"][nside] = dict()

        if "MillipedeStarting2ndPass_millipedellh" in frame:
            llh = frame["MillipedeStarting2ndPass_millipedellh"].logl
        else:
            llh = numpy.nan

        # save in output dict
        scan_dict["nsides"][nside][pixel] = dict(frame=frame, llh=llh)

        # save to file
        nside_dir = os.path.join(this_event_cache_dir, "nside{0:06d}".format(nside))
        if not os.path.exists(nside_dir):
            os.mkdir(nside_dir)
        pixel_file_name = os.path.join(nside_dir, "pix{0:012d}.i3".format(pixel))

        print " - importing pixel file {0}...".format(pixel_file_name)
        save_GCD_frame_packet_to_file([frame], pixel_file_name)

    print "import done."

    return (event_id_string, scan_dict)


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)
    parser.add_option("-c", "--cache-dir", action="store", type="string",
        default="./cache/", dest="CACHEDIR", help="The cache directory to use")
    parser.add_option("-g", "--override-GCD-filename", action="store", type="string",
        default=None, dest="OVERRIDEGCDFILENAME", help="Use this GCD baseline file instead of the one referenced by the message")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one event file to import")
    filename = args[0]

    # get the file stager instance
    stagers = dataio.get_stagers()

    packets = import_old_style_scan(filename, filestager=stagers, cache_dir=options.CACHEDIR, override_GCD_filename=options.OVERRIDEGCDFILENAME)

    print "got:", packets
