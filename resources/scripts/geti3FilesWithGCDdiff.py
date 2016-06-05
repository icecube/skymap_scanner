#!/usr/bin/env python

from icecube import icetray, dataio, dataclasses
import json
import datetime
import urllib, urllib2, zmq
import cPickle as pickle
import zlib, base64
from collections import OrderedDict

def json_to_frame_packet(json_msg):
    """Ripping off icerec/full_event_followup"""
    assert isinstance(json_msg, dict)
    frame_packets = []

    for keytype, compressed_string in json_msg.iteritems():
        frame = pickle.loads( zlib.decompress(
                base64.b64decode( compressed_string) )
                )
        frame_packets.append(frame)
    return frame_packets

def GetDataBaseOutput(varname='heseEvent16', topic='heseEvent16',
                starttime=datetime.datetime.now()-datetime.timedelta(days=1),
                stoptime =datetime.datetime.now()):
    """Queries the database, parse with json.loads, returns output

    **Nearly a replicate of I3LiveTools/QueryDataBase**
    ** Hopefully helps followup-devs see how to implement rest of code **
    Default behavior is to look in the last 24 hours for
    any HESE full followups

    **2016**
    Various streams and their varnames/topics:
      - HESE full followup: heseEvent16Data
      - HESE full followup (low prio): subThreshold_heseEvent16Data
      - EHE full followup: eheEvent16Data

    **2015**
      - heseEvent/heseEventFull"""
    url = 'https://live.icecube.wisc.edu/pfow_data/'

    req = urllib2.Request(url,
                urllib.urlencode(
                {'user':'icecube', 'pass':'skua',
                'varname':varname, 'topic':topic,
                'timekey':'time', 'start':starttime, 'stop':stoptime})
                )
    response = urllib2.urlopen(req).read()
    db_output = json.loads(response)

    data = []
    for db_entry in db_output:
        event = db_entry['value']['data']
        if isinstance(event, list):
            event = {t[0]:t[1:][0] for t in event}
        event['topic'] = db_entry['value']['zmqnotify']['topics']
        event['varname'] = db_entry['varname']
        data.append(event)

    return data

if __name__ == "__main__":
    """data is self.data in the followup framework"""
    data = GetDataBaseOutput(varname="subThreshold_heseEvent16Data",
            topic="subThreshold_heseEvent16Data",
            starttime=datetime.datetime.now()-datetime.timedelta(days=3),
            )
    print 'Found {} events'.format( len(data))

    """Get rid of varname and topic info"""
    ## If only QP frames desired, remove GCD elements from goodkeys
    goodkeys = ['G','C','D','Q','P']
    GCDQPdicts = []
    for event in data:
        GCDQPdict = OrderedDict()
        for goodkey in goodkeys:
            GCDQPdict.__setitem__(goodkey, event[goodkey])
        GCDQPdicts.append(GCDQPdict)


    """Save the list of dictionaries after converting them"""
    i3fname = 'GCDQPframes.i3.bz2'
    i3file = dataio.I3File()
    i3file.open_file(i3fname, dataio.I3File.Writing)

    for event in GCDQPdicts:
        frame_packet = json_to_frame_packet(event)
        for frame in frame_packet:
            print frame
            i3file.push(frame)
    i3file.close()
    print "{} saved".format(i3fname)
