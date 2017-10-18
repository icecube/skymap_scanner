import os
import numpy

from icecube import icetray, dataclasses, dataio
from icecube import gulliver, millipede

from utils import save_GCD_frame_packet_to_file, create_event_id
from extract_json_message import __extract_frame_packet

def import_simulation_p_frame(filename, filestager, frame_number=1, cache_dir="./cache/", override_GCD_filename=None):
    i3f = dataio.I3File(filename, 'r')

    # read GCDQp
    GCDQp_packet = []
    GCDQp_packet.append(i3f.pop_frame())
    if GCDQp_packet[-1].Stop == icetray.I3Frame.TrayInfo:
        GCDQp_packet[-1] = i3f.pop_frame()
    if GCDQp_packet[-1].Stop != icetray.I3Frame.Geometry:
        raise RuntimeError("No G-frame in input file")
    GCDQp_packet.append(i3f.pop_frame())
    if GCDQp_packet[-1].Stop != icetray.I3Frame.Calibration:
        raise RuntimeError("No C-frame in input file")
    GCDQp_packet.append(i3f.pop_frame())
    if GCDQp_packet[-1].Stop != icetray.I3Frame.DetectorStatus:
        raise RuntimeError("No D-frame in input file")
    
    last_M_frame = None
    last_Q_frame = None
    last_P_frame = None

    current_p_frame_num = 0
    while i3f.more():
        fr = i3f.pop_frame()
        if fr.Stop != icetray.I3Frame.DAQ and fr.Stop != icetray.I3Frame.Stream('M') and fr.Stop != icetray.I3Frame.Physics:
            raise RuntimeError("Unknown frame type encountered")

        if fr.Stop == icetray.I3Frame.DAQ:
            last_Q_frame = fr
            continue

        if fr.Stop == icetray.I3Frame.Stream('M'):
            last_M_frame = fr
            continue

        if fr.Stop != icetray.I3Frame.Physics:
            raise RuntimeError("Internal logic error")

        current_p_frame_num += 1

        if current_p_frame_num < frame_number:
            continue
        
        last_P_frame = fr
        break

    if last_P_frame is None:
        raise RuntimeError("No P-frame at index {0} found. Only saw {1} P-frames.".format(frame_number, current_p_frame_num))

    if last_M_frame is not None:
        GCDQp_packet.append(last_M_frame)

    if last_Q_frame is not None:
        GCDQp_packet.append(last_Q_frame)

    GCDQp_packet.append(last_P_frame)

    print "importing GCDQp..."
    this_event_cache_dir, event_id_string, scan_dict = __extract_frame_packet(GCDQp_packet, filestager, cache_dir=cache_dir, override_GCD_filename=override_GCD_filename, pulsesName="SplitUncleanedInIcePulses")

    if "nsides" not in scan_dict: scan_dict["nsides"] = dict()

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
    parser.add_option("-n", "--p-frame-index", action="store", type="int",
        default=1, dest="INDEX", help="use the nth P-frame in the input file for the scan (INDEX=n)")

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exactly one event file to import")
    filename = args[0]

    # get the file stager instance
    stagers = dataio.get_stagers()

    packets = import_simulation_p_frame(filename, filestager=stagers, frame_number=options.INDEX, cache_dir=options.CACHEDIR, override_GCD_filename=options.OVERRIDEGCDFILENAME)

    print "got:", packets
