'''
Could be useful to have a logger that can optionally post to slack?

from logging import Logger

class FlexiLogger(Logger):
    # untested; not sure this works because of how super() is resolved
    log_func = { 'info':super().info, 'debug':super().debug, 'warning':super().warning, 'error':super().error }

    def __init__(self, SlackInterface):
        self.slack = SlackInterface
        self.log = logging.getLogger(__name__)

    def log(level='info', slack=False, message=None):
        if slack:
            self.slack.post(message)
        self.log_func[level](message)
'''
