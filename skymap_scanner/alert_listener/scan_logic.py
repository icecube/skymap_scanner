"""Consolidated scan logic."""

# fmt: off
# pylint: skip-file

import json

import numpy as np
from icecube.realtime_ehe import EHE_alerts_v2
from icecube.realtime_gfu import muon_alerts
from icecube.realtime_hese import HESE_alerts_v2

# ==============================================================================
# Map each alert_eval function to its corresponding alert stream name
# ==============================================================================

stream_logic_map = {
    "EHE": EHE_alerts_v2.ehe_alert_eval,
    "HESE": HESE_alerts_v2.hese_alert_eval,
    "neutrino": muon_alerts.gfu_alert_eval
}


# ==============================================================================
# Helper function to extract json message from raw alert message
# ==============================================================================

def convert_short_message(raw_short_message):
    """Function to convert the raw 'Short alert message', in I3String format,
    stored within the 'full alert message' to the format expected by the
    x_alert_eval functions.

    :param raw_short_message: Short alert message (I3String format)
    :return: Short alert message packed in appropriate dictionary structure
    """
    return {"value": {"data": json.loads(raw_short_message.value)}}


def extract_short_message(p_frame, post_to_slack):
    short_key = 'AlertShortFollowupMsg'

    if short_key not in list(p_frame.keys()):
        post_to_slack(
            "Cannot assess event using V2 alert logic, as `{0}` is missing from the P Frame. "
            "Available keys are `{1}`".format(short_key, list(p_frame.keys())))
        post_to_slack("I will have to assume that no scan is needed. You "
                      "should probably check that.")
        return False

    alert_dict = convert_short_message(p_frame[short_key])
    return alert_dict


# ==============================================================================
# Define logic functions to determine is an event should be scanned
# ==============================================================================

def generic_alert_logic(p_frame, alert_eval_f, post_to_slack, short_message=None):
    """Apply logic for determining whether a given event is an
    alert worthy of scanning, or whether it is subthreshold and can be ignored.

    :param p_frame: Physics frame extracted from json
    :param alert_eval_f: Function used to evaluate an alert dictionary
    :param post_to_slack: Function used to post slack messages
    :return: Boolean True/False for whether event should be scanned
    """
    if short_message is None:
        alert_dict = extract_short_message(p_frame, post_to_slack)
    else:
        alert_dict = short_message
    alert_eval = alert_eval_f(alert_dict)
    if alert_eval["pass_loose"]:
        post_to_slack("Alert evaluation:`{0}`".format(alert_eval))

    if alert_eval["pass_tight"]:
        return "Gold"
    elif alert_eval["pass_loose"]:
        return "Bronze"
    else:
        return False


def subthreshold_hese_logic(p_frame, post_to_slack):
    """Even if a HESE event does not qualify for an alert, we will still scan
    those with causal qtot above 6000.

    :param p_frame: Physics frame extracted from json
    :param post_to_slack: Function used to post slack messages
    :return: Boolean True/False for whether event should be scanned
    """
    qtot_key = "HESE_CausalQTot"

    if qtot_key not in list(p_frame.keys()):
        post_to_slack(
            "Cannot assess event, as `{0}` is missing from the P Frame. "
            "Available keys are `{1}`".format(qtot, list(p_frame.keys())))
        post_to_slack("I will have to assume that no HESE scan is needed. You "
                      "should probably check that.")
        return False

    causal_qtot = p_frame[qtot_key].value
    if causal_qtot >= 6000.:
        post_to_slack(
            "Found a HESE event with Qtot>6000. It could be an older alert, "
            "or a newer subthreshold event. I will scan it.")
        return True
    else:
        return False


def backward_compatible_ehe_logic(post_to_slack):
    """Any event which is tagged as EHE should be scanned. If for some reason
    the generic logic fails, this failsafe will ensure an alert is scanned

    :param post_to_slack: Function used to post slack messages
    :return: True
    """
    post_to_slack("Found an old EHE event. It is missing a 'short message', "
                  "but I will scan it anyway.")
    return True


# ==============================================================================
# Combined logic function to be called by listener
# ==============================================================================

def whether_to_scan(p_frame, alert_streams, notify_alert, post_to_slack, short_message=None):
    """Logic function to determine whether a given event should be scanned.
    By default, it loops over the realtime alert eval functions to determine
    whether an alert should be scanned. If an event fails all these
    functions, an additional test is done is identify sub-threshold HESE
    events with Qtot >6000, which are scanned despite not generating alerts.
    This step ensures backward-compatibility with V1 HESE alerts that did not
    contain the 'short message' summaries. Lastly, a backwards-compatibility
    check is done to ensure all alerts tagged with EHE are scanned. Returns a
    boolean do_scan, which is True if at least one criteria is fulfilled.

    :param p_frame: Physics frame
    :param alert_streams: Full list of tagged streams
    :param notify_alert: Message that should be sent out when an alert is to
    be scanned. Typically 'live' listeners notify @channel when an alert is
    found, but listeners for replayed streams do not.
    :param post_to_slack: Function used to post slack messages

    :return: Boolean do_scan
    """

    do_scan = False

    # Loop over each tagged realtime stream, and check whether the event
    # passes the alert criteria using that streams alert_eval function. If
    # streams do not have associated logic functions, they will be ignored.

    for key in alert_streams:
        try:
            alert_eval = generic_alert_logic(p_frame, stream_logic_map[key],
                                             post_to_slack, short_message)
            # If there is a match to Gold/Bronze
            if np.logical_and(not do_scan, alert_eval is not False):
                post_to_slack(notify_alert.format(key, alert_eval))
                do_scan = True
            # If there are additional matches
            elif alert_eval is not False:
                post_to_slack("This is also {0} {1} Alert.".format(
                    key, alert_eval))
        except KeyError:
            pass
        except AttributeError:
            pass

    # Check for subthreshold HESE alerts with Qtot > 6000

    if np.logical_and(not do_scan, "HESE" in alert_streams):
        do_scan = subthreshold_hese_logic(p_frame, post_to_slack)
        if do_scan:
            post_to_slack(notify_alert.format("HESE", "subthreshold"))

    # Check for stray EHE events without 'short message'.

    if np.logical_and(not do_scan, "EHE" in alert_streams):
        do_scan = backward_compatible_ehe_logic(post_to_slack)
        if do_scan:
            post_to_slack(notify_alert.format("EHE", "subthreshold"))     
    return do_scan
