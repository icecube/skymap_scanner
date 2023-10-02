"""Entry-point to start up client service."""

from . import LOGGER, client

if __name__ == "__main__":
    client.main()
    LOGGER.info("Done.")
