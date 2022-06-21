# code adapted from python/prepare_frames.py 

from icecube import icetray

class ListReader(icetray.I3Module):
    def __init__(self, ctx):
        super(ListReader, self).__init__(ctx)
        self.AddParameter("Frames", "Frames to push to modules downstream", list())
        self.AddOutBox("OutBox")

    def Configure(self):
        self.frames = copy(self.GetParameter("Frames"))

    def Process(self):
        if self.PopFrame():  # ensure this is a driving module
            raise RuntimeError("FrameArrayReader needs to be used as a driving module")

        if len(self.frames) == 0:  # queue is empty
            self.RequestSuspension()
            return

        self.PushFrame(self.frames.pop(0))  # push the frontmost item


class ListWriter(icetray.I3Module):
    def __init__(self, ctx):
        super(ListWriter, self).__init__(ctx)
        self.AddParameter("FrameStore", "Output list for processed frames", list())
        self.AddOutBox("OutBox")

    def Configure(self):
        self.frame_store = self.GetParameter("FrameStore")

    def Process(self):
        frame = self.PopFrame()
        if not frame:
            return

        if frame.Stop == icetray.I3Frame.TrayInfo:  # ignore potential TrayInfo frames
            self.PushFrame(frame)
            return

        self.frame_store.append(frame)

        self.PushFrame(frame)
