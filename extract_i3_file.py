from __future__ import print_function
from __future__ import absolute_import


try:
    from tempfile import TemporaryDirectory
except:
    from backports.tempfile import TemporaryDirectory

from tqdm import tqdm

import re
import copy
import glob
import os
import shutil
import subprocess

import config

from icecube import icetray, dataclasses, dataio
from I3Tray import I3Tray

from icecube.frame_object_diff.segments import compress

class FrameArraySink(icetray.I3Module):
    def __init__(self, ctx):
        super(FrameArraySink, self).__init__(ctx)
        self.AddParameter("FrameStore", "Array to which to add frames", [])
        self.AddParameter("SuspendAfterStop", "", None)
        self.AddOutBox("OutBox")

    def Configure(self):
        self.frame_store = self.GetParameter("FrameStore")
        self.suspend_after_stop = self.GetParameter("SuspendAfterStop")

    def Process(self):
        frame = self.PopFrame()
        if not frame: return

        # ignore potential TrayInfo frames
        if frame.Stop == icetray.I3Frame.TrayInfo:
            self.PushFrame(frame)
            return

        frame_copy = copy.copy(frame)
        frame_copy.purge()
        self.frame_store.append(frame_copy)
        del frame_copy

        self.PushFrame(frame)
        
        if self.suspend_after_stop is not None:
            if self.suspend_after_stop == frame.Stop:
                self.RequestSuspension()

def extract_i3_file_gcd_diff(url, baseline_gcd, stop_after_first_p_frame=True):
    frame_packet = []
    
    if stop_after_first_p_frame:
        SuspendAfterStop = icetray.I3Frame.Physics
    else:
        SuspendAfterStop = None
    
    icetray.set_log_level_for_unit('I3Tray', icetray.I3LogLevel.LOG_WARN)
    
    tray = I3Tray()
    
    tray.Add("I3Reader", "reader", FilenameList=[url])
    
    if baseline_gcd is not None:
        tray.Add(compress, "GCD_diff",
            base_filename=baseline_gcd,
            base_path=config.base_GCD_path)
    
    tray.Add(FrameArraySink, "FrameArraySink",
        FrameStore=frame_packet,
        SuspendAfterStop=SuspendAfterStop)
    tray.Execute()
    del tray

    icetray.set_log_level_for_unit('I3Tray', icetray.I3LogLevel.LOG_NOTICE)

    return frame_packet

def extract_i3_file(url, stop_after_first_p_frame=True):
    possible_baseline_gcds = glob.glob(config.base_GCD_path+"/*.i3")

    # get a file stager
    stagers = dataio.get_stagers()

    with TemporaryDirectory() as temp_dir:
        uncompressed_filename = os.path.join(temp_dir, "working.i3")

        blob_handle = stagers.GetReadablePath( url )
        if not os.path.isfile( str(blob_handle) ):
            print("problem reading i3 file from {0}".format( url ))
            raise RuntimeError("problem reading i3 file from {0}".format( url ))

        print("Uncompressing {} to {}".format(str(blob_handle), uncompressed_filename))

        _, file_ext = os.path.splitext(str(blob_handle))
        
        if file_ext == '.zst':
            ret = subprocess.call(['/usr/bin/zstd', '-d', str(blob_handle), '-o', uncompressed_filename])
            if ret != 0:
                raise RuntimeError("Could not decompress .zst file {}".format(url))
        elif file_ext == '.bz2':
            with open(uncompressed_filename, 'wb') as f:
                ret = subprocess.call(['/bin/bzip2', '-k', '-d', '--stdout', str(blob_handle)], stdout=f)
            if ret != 0:
                raise RuntimeError("Could not decompress .bz2 file {}".format(url))
        elif file_ext == '.xz':
            with open(uncompressed_filename, 'wb') as f:
                ret = subprocess.call(['/usr/bin/xz', '-k', '-d', '--stdout', str(blob_handle)], stdout=f)
            if ret != 0:
                raise RuntimeError("Could not decompress .xz file {}".format(url))
        elif file_ext == '.gz':
            with open(uncompressed_filename, 'wb') as f:
                ret = subprocess.call(['/bin/gzip', '-k', '-d', '--stdout', str(blob_handle)], stdout=f)
            if ret != 0:
                raise RuntimeError("Could not decompress .gz file {}".format(url))
        else:
            shutil.copyfile(str(blob_handle), uncompressed_filename)
        
        del blob_handle

        
        
        print("Reading the original file to judge its size..")
        frame_packet = extract_i3_file_gcd_diff(uncompressed_filename, baseline_gcd=None, stop_after_first_p_frame=stop_after_first_p_frame)
        original_size = 0
        for frame in frame_packet:
            original_size += len(frame.dumps())
        del frame_packet
        print("Done. It is {}MiB in size".format(original_size/1024/1024))

        print("Applying each available GCD diff to this undiffed data to see which one works best...")
        serialized_sizes = {}
        with tqdm(possible_baseline_gcds) as pbar:
            for baseline_gcd in pbar:
                _, baseline_gcd_file = os.path.split(baseline_gcd)
                pbar.set_postfix(GCD_file=baseline_gcd_file)

                frame_packet = extract_i3_file_gcd_diff(uncompressed_filename, baseline_gcd=baseline_gcd_file, stop_after_first_p_frame=stop_after_first_p_frame)

                this_size = 0
                for frame in frame_packet:
                    this_size += len(frame.dumps())

                serialized_sizes[this_size] = (baseline_gcd, frame_packet)


    sizes = sorted(serialized_sizes.keys())
    _, best_baseline_gcd = os.path.split(serialized_sizes[sizes[0]][0])
    best_frame_packet = serialized_sizes[sizes[0]][1]
    del serialized_sizes
    
    print("Best GCD baseline file for this data is {} and yields a size of {}MiB. The worst one is {} kiB larger.".format(
        best_baseline_gcd, sizes[0]/1024/1024, (sizes[-1]-sizes[0])/1024
    ))
    
    return best_frame_packet
