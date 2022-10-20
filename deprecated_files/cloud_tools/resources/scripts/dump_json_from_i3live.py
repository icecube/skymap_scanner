#!/usr/bin/env python

from __future__ import print_function

try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError
    
import json
import time
import re
from datetime import datetime
from optparse import OptionParser


DEFAULT_SERVICE_NAME = "PFOnlineWriter"
DEFAULT_VARNAME = "realtimeEventData"
DEFAULT_TIME_KEY = "time"
DEFAULT_START_TIME = str(datetime(1900, 1, 1))
DEFAULT_STOP_TIME = str(datetime.max)
DEFAULT_URL = "https://live.icecube.wisc.edu/moni_access/"

def str2datetime(dtstr):
    """
    Copy from I3Live for time string sanity checking
    """
    if dtstr is None:
        return None
    dtpat = "(\d{4})-(\d\d)-(\d\d).+?(\d\d):(\d\d):(\d\d)(?:\.(\d+))?"
    dm = re.search(dtpat, dtstr)
    if not dm:
        return None
    usec = 0
    usecstr = dm.group(7)
    if usecstr:
        assert len(usecstr) >= 6
        usec = int(dm.group(7)[:6])
    return datetime(int(dm.group(1)),
                    int(dm.group(2)),
                    int(dm.group(3)),
                    int(dm.group(4)),
                    int(dm.group(5)),
                    int(dm.group(6)),
                    usec)


def getRecords(user=None,
               passwd=None,
               varname=None,
               service=None,
               timeKey=None,
               startTime=None,
               stopTime=None,
               url=None):

    query = {}
    query["user"] = user
    query["pass"] = passwd
    query["varname"] = varname
    query["service"] = service
    query["timekey"] = timeKey
    query["start"] = startTime
    query["stop"] = stopTime

    data = urlencode(query).encode('utf-8')
    req = Request(url, data)
    resp = urlopen(req, timeout=30)
    return json.loads(resp.read())


def isTimeStringValid(timeStr):
    try:
        return str2datetime(timeStr) is not None
    except:
        return False


def main():

    parser = OptionParser()
    parser.add_option("-u", "--username", dest="username", default="icecube",
                      help="I3Live URL post user name.\nDefault: icecube")
    parser.add_option("-p", "--pass", dest="passwd",
                      help="I3Live URL post user password")
    parser.add_option("-v", "--varname", dest="varname",
                      default=DEFAULT_VARNAME,
                      help="varname of data to be replayed")
    parser.add_option("-s", "--service", dest="service",
                      default=DEFAULT_SERVICE_NAME,
                      help="service name of monitoring data to be replayed.\n"
                           "Default: %s" % DEFAULT_SERVICE_NAME)
    parser.add_option("--timeKey", dest="timeKey",
                      default=DEFAULT_TIME_KEY,
                      help="Key name for start/stop times.\n"
                           "Default: '%s'" % DEFAULT_TIME_KEY)
    parser.add_option("--start", dest="start",
                      default=DEFAULT_START_TIME,
                      help="Start time for monitoring data.\n"
                           "Default: '%s'" % DEFAULT_START_TIME)
    parser.add_option("--stop", dest="stop",
                      default=DEFAULT_STOP_TIME,
                      help="Stop time for monitoring data.\n"
                           "Default: '%s'" % DEFAULT_STOP_TIME)
    parser.add_option("--url", dest="url", default=DEFAULT_URL,
                      help="I3Live monitoring URL.\nDefault: %s" % DEFAULT_URL)

    (options, args) = parser.parse_args()
    if options.passwd == None:
        print("Bad options: password must be specified")
        parser.print_help()
        return

    if not isTimeStringValid(options.start):
        print("Bad start time string: '%s'" % options.start)
        parser.print_help()
        return

    if not isTimeStringValid(options.stop):
        print("Bad stop time string: '%s'" % options.stop)
        parser.print_help()
        return

    records = getRecords(user=options.username,
                         passwd=options.passwd,
                         varname=options.varname,
                         service=options.service,
                         timeKey=options.timeKey,
                         startTime=options.start,
                         stopTime=options.stop,
                         url=options.url)

    if len(records) == 0:
        print("No records found.")
        return

    if len(records) > 1:
        print("Multiple records found")
        # rec = [json.dumps(e) for e in records]
        # print(rec[0])
        return
        
    rec = records[0]
    
    print(json.dumps(rec))


if __name__ == '__main__':
    main()
