import config
import json
import requests

API_BASE_URL = 'https://slack.com/api/{api}'

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
            'username': 'scanner-bot',
            'icon_emoji': ':mag:',
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
    
