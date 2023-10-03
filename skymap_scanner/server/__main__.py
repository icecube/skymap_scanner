"""Entry-point to start up server."""

from . import LOGGER, start_scan

if __name__ == "__main__":
    start_scan.main()
    LOGGER.info("Done.")
