import json
import requests
import logging

API_BASE_URL = 'https://slack.com/api/{api}'

# ========
# NEW CODE
# ========

'''
This file is tentatively linked from `python` to `resources/scripts` so it can be directly imported in `alert_v2_listener.py`. Waiting for the conversion into a python package.

The idea is to handle the slack posting and messages through dedicated classes.
'''


class SlackError(Exception):
    pass


class SlackResponse(object):
    def __init__(self, body):
        self.raw = body
        self.body = json.loads(body)
        self.successful = self.body['ok']
        self.error = self.body.get('error')


class SlackInterface():
    def __init__(self, whoami=""):
        self.name = whoami
        self.logger = logging.getLogger(__name__)

    def set_channel(self, channel):
        self.channel = channel

    def set_api_key(self, api_keyfile):
        with open(api_keyfile, "r") as f:
            key = f.read().rstrip()
            # rstrip() needed to drop trailing newline
        self.api_key = key

    def post(self, msg):
        # never crash because of Slack
        try:
            self.logger.info(msg)
            return self.post_message(self.name + " " + msg)
        except Exception as err:
            self.logger.warning(f"Posting to Slack failed because of: {err}")

    def upload_file(self, file_handle, filename, title):
        api = 'files.upload'

        response = requests.post(
            API_BASE_URL.format(api=api),
            timeout=60,
            params={'token': self.api_key},
            data={
                # 'content': content,
                # 'filetype': filetype,
                'filename': filename,
                'title': title,
                # 'initial_comment': initial_comment,
                'channels': self.channel
            },
            files={'file': file_handle}
        )

        response.raise_for_status()
        response = SlackResponse(response.text)

        if not response.successful:
            raise SlackError(response.error)

        return response

    def post_message(self, text):
        api = 'chat.postMessage'

        response = requests.post(
            API_BASE_URL.format(api=api),
            timeout=10,
            params={'token': self.api_key},
            data={
                'text': text,
                'channel': self.channel,
                'as_user': False,
                'username': 'Marvin-the-Paranoid-Android',
                'icon_emoji': ':disappointed:',
            }
        )

        response.raise_for_status()

        response = SlackResponse(response.text)
        if not response.successful:
            raise SlackError(response.error)

        return response


class MessageHelper():
    def __init__(self):
        pass

    def intermediate_scan(event_id: str):
        msg = f"I am creating a plot of the current status of the scan of `{event_id}` for you. This should only take a minute."
        return msg

    def finish_message(event_id: str, event_cache_dir: str):
        msg = f"Okay, that's it. I'm finished with this `{event_id}`. Look for the cache in `{event_cache_dir}`"
        return msg

    def switch_on(source, send_scans):
        msg = f"Switching on. I will now listen to the stream from `{source}`. Sending scans is toggled to `{send_scans}`."
        return msg

    def switch_off(shifters_slackid, exception_message):
        msg = f'Switching off. {shifters_slackid}, something went wrong with the listener (python caught an exception): ```{exception_message}``` *I blame human error*'
        return msg

    def scan_fail(shifters_slackid, exception_message):
        msg = f'Switching off. {shifters_slackid},  something went wrong while scanning the event (python caught an exception): ```{exception_message}``` *I blame human error*'
        return msg

    def sub_threshold():
        msg = "This event is subthreshold. No scan is needed."
        return msg

    def nokey_value():
        msg = 'incoming message is invalid - no key named "value" in message'
        return msg

    def nokey_streams():
        msg = 'incoming message is invalid - no key named "streams" in event["value"]'
        return msg

    def new_event(run, evt, alert_streams):
        msg = f'New event found, `{run}`, `{evt}`, tagged with alert streams: `{alert_streams}`'
        return msg

    def scanning_done(event_id):
        msg = f"Scanning of `{event_id}` is done. Let me create a plot for you real quick."
        return msg

    def new_gfu(run, evt, frac):
        msg = f"New GFU-only event found, `{run}`, `{evt}`, with Passing Fraction: {frac}. It's probably sub-threshold, but I'll check it anyway. *sigh*"
        return msg

    def missing_header(event_id):
        msg = f"Something is wrong with this event (ID `{event_id}`). Its P-frame doesn't have a header... I will try to continue with submitting the scan anyway, but this doesn't look good."
        return msg

    def scan_disabled():
        msg = "Scanning Mode is disabled! No scan will be performed."
        return msg


if __name__ == "__main__":
    from optparse import OptionParser
    from load_scan_state import load_cache_state

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)

    # get parsed args
    (options, args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exactly one message")
    message = args[0]

    slack = SlackInterface()
    slack.post(message)
