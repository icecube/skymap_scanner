from . import config
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

class SlackInterface():
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def post(self, msg):
        # never crash because of Slack
        try:
            self.logger.info(msg)
            return post_message(text)
        except Exception as err:
            logger.warning(f"Posting to Slack failed because of: {err}")

    def upload_file(self, file_handle, filename, title):
        return upload_file(file_handle, filename, title)


class MessageHelper():
    def __init__(self):
        pass

    def intermediate_scan(self, event_id : str):
        msg = f"I am creating a plot of the current status of the scan of `{event_id}` for you. This should only take a minute."
        return msg

    def finish_message(self, event_id : str, event_cache_dir : str)
        msg = f"Okay, that's it. I'm finished with this `{event_id}`. Look for the cache in `{event_cache_dir}`"
        return msg

    def switch_on(self, source, send_scans):
        msg = f"Switching on. I will now listen to the stream from `{source}`. Sending scans is toggled to `{send_scans}`."
        return msg

    def switch_off(self, shifters_slackid, exception_message):
        msg = f'Switching off. {shifters_slackid}, something went wrong with the listener (python caught an exception): ```{exception_message}``` *I blame human error*'
        return msg


# ===
# OLD CODE
# === 

class Error(Exception):
    pass

class Response(object):
    def __init__(self, body):
        self.raw = body
        self.body = json.loads(body)
        self.successful = self.body['ok']
        self.error = self.body.get('error')

def upload_file(file_handle, filename, title):
    api = 'files.upload'

    response = requests.post(
        API_BASE_URL.format(api=api),
        timeout=60,
        params={'token': config.slack_api_key},
        data={
            # 'content': content,
            # 'filetype': filetype,
            'filename': filename,
            'title': title,
            # 'initial_comment': initial_comment,
            'channels': config.slack_channel
        },
        files={'file': file_handle}
        )

    response.raise_for_status()

    response = Response(response.text)
    if not response.successful:
        raise Error(response.error)

    return response

def post_message(text):
    api = 'chat.postMessage'

    response = requests.post(
        API_BASE_URL.format(api=api),
        timeout=10,
        params={'token': config.slack_api_key},
        data={
            'text': text,
            'channel': config.slack_channel,
            'as_user': False,
            'username': 'Marvin-the-Paranoid-Android',
            'icon_emoji': ':disappointed:',
        }
        )

    response.raise_for_status()

    response = Response(response.text)
    if not response.successful:
        raise Error(response.error)

    return response

if __name__ == "__main__":
    from optparse import OptionParser
    from load_scan_state import load_cache_state

    parser = OptionParser()
    usage = """%prog [options]"""
    parser.set_usage(usage)

    # get parsed args
    (options,args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("You need to specify exatcly one message")
    message = args[0]

    post_message(message)

