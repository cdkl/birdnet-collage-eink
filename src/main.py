import os
import sys
import time
import signal
import logging

from .display import create_display
from .fetcher import CollageFetcher

log = logging.getLogger(__name__)

COLLAGE_URL = os.getenv("COLLAGE_URL", "http://localhost:8081")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))
DISPLAY_DRIVER = os.getenv("DISPLAY_DRIVER", "simulator")
DISPLAY_WIDTH = int(os.getenv("DISPLAY_WIDTH", "1600"))
DISPLAY_HEIGHT = int(os.getenv("DISPLAY_HEIGHT", "1200"))
CACHE_DIR = os.getenv("CACHE_DIR", "/var/lib/birdnet-eink")
FORCE_REFRESH = int(os.getenv("FORCE_REFRESH", "0"))
SATURATION = float(os.getenv("SATURATION", "0.5"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

_display = None


def _handle_signal(signum, frame):
    log.info("Received signal %d, shutting down...", signum)
    if _display is not None:
        _display.clear()
    sys.exit(0)


def _poll_loop(display, fetcher):
    while True:
        png, etag = fetcher.fetch(
            width=DISPLAY_WIDTH,
            height=DISPLAY_HEIGHT,
            hours=LOOKBACK_HOURS,
            refresh=FORCE_REFRESH,
        )
        if png is not None:
            display.show(png)
            if etag:
                fetcher.save_etag(etag)
        else:
            log.debug("Skipping display update (no new data)")

        time.sleep(POLL_INTERVAL)


def main():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    global _display
    _display = create_display(DISPLAY_DRIVER, saturation=SATURATION)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    fetcher = CollageFetcher(COLLAGE_URL, cache_dir=CACHE_DIR)

    log.info(
        "Starting birdnet-collage-eink: %s → %s every %ds (lookback=%dh, refresh=%d, saturation=%.2f)",
        COLLAGE_URL, DISPLAY_DRIVER, POLL_INTERVAL, LOOKBACK_HOURS, FORCE_REFRESH, SATURATION,
    )

    _poll_loop(_display, fetcher)


if __name__ == "__main__":
    main()