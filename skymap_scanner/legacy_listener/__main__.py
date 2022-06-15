"""Entry-point to start up alert listener service."""

from . import alert_v2_listener

if __name__ == "__main__":
    alert_v2_listener.main()
