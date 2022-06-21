import logging
import os
import pickle
import subprocess

from realtime_event import RealtimeEvent


class EventHandler:
    def __init__(self, cache_manager, process=True):
        self.cache = cache_manager
        self.log = logging.getLogger(__name__)
        self.process = process

    def __call__(self, varname, topics, event):
        self.handle_event(varname, topics, event)

    def handle_event(self, varname, topics, event):
        evt = RealtimeEvent(event)

        cache_dir = self.cache.dir

        try:
            stem = evt.get_stem()
        except KeyError as err:
            self.log.error(
                f"The payload of the pending event is missing or incomplete. Error: {err}"
            )
            return

        # TODO: replace with pathlib Path for readability?
        event_filepath = os.path.join(cache_dir, stem + ".pkl")
        log_filepath = os.path.join(cache_dir, stem + ".log")

        self.log.info(f"Writing incoming event to {event_filepath}")
        with open(event_filepath, "wb") as event_file:
            pickle.dump(event, event_file)

        alert_processor = (
            os.path.dirname(os.path.abspath(__file__)) + "/alert_processor.py"
        )

        if self.process:
            self.log.info(f"Processing event with subprocess, check {log_filepath}")
            cmd = ["python", alert_processor, "-e", event_filepath]

            with open(log_filepath, "w") as logfile:
                subprocess.run(
                    cmd,
                    stdout=logfile,
                    stderr=subprocess.STDOUT,
                )
