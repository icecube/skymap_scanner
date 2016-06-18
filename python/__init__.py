#
# Copyright (c) 2016
# Claudio Kopper <claudio.kopper@icecube.wisc.edu>
# and the IceCube Collaboration <http://www.icecube.wisc.edu>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION
# OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
#
# $Id$
#
# @file __init__.py
# @version $Revision$
# @date $Date$
# @author Claudio Kopper
#

from icecube.load_pybindings import load_pybindings
from icecube import icetray, dataclasses # be nice and pull in our dependencies
load_pybindings(__name__,__path__)

import config
from extract_json_messages import extract_json_message, extract_json_messages
from load_scan_state import load_scan_state, load_cache_state, load_GCDQp_state
from import_old_style_scan import import_old_style_scan
from perform_scan import perform_scan
from utils import create_event_id, load_GCD_frame_packet_from_file, save_GCD_frame_packet_to_file, hash_frame_packet, rewrite_frame_stop, parse_event_id

import traysegments

# clean up the namespace
del icetray
del dataclasses
