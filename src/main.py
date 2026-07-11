import os
import sys
import time
import signal
import logging
import threading

from .display import create_display
from .display.base import overlay_timestamp
from .fetcher import CollageFetcher
from .diagnostics import DiagnosticsState, DiagnosticsServer

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
DIAGNOSTICS_PORT = int(os.getenv("DIAGNOSTICS_PORT", "8082"))
BUTTONS_ENABLED = int(os.getenv("BUTTONS_ENABLED", "0"))

_display = None
_diag_state = DiagnosticsState()

SHUTDOWN_IMAGE = "shutdown.png"


def _shutdown_image_path():
    return os.path.join(os.path.dirname(__file__), "..", SHUTDOWN_IMAGE)


def _save_diagnostic_original(png_bytes, cache_dir):
    path = os.path.join(cache_dir, "last-original.png")
    try:
        with open(path, "wb") as f:
            f.write(png_bytes)
    except OSError as e:
        log.warning("Failed to save diagnostic original image: %s", e)


def _save_diagnostic_quantized(display, cache_dir):
    if display.last_quantized_bytes is None:
        return
    path = os.path.join(cache_dir, "last-quantized.png")
    try:
        with open(path, "wb") as f:
            f.write(display.last_quantized_bytes)
    except OSError as e:
        log.warning("Failed to save diagnostic quantized image: %s", e)


def _handle_signal(signum, frame):
    log.info("Received signal %d, shutting down...", signum)
    if _display is not None:
        path = _shutdown_image_path()
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    _display.show(f.read())
                log.info("Shutdown image displayed")
            except Exception as e:
                log.warning("Failed to display shutdown image: %s", e)
                _display.clear()
        else:
            _display.clear()
    sys.exit(0)


def _poll_loop(display, fetcher, diag_state, cache_dir, button_state=None):
    first_poll = True
    while True:
        if button_state is not None:
            if button_state["clear_requested"]:
                display.clear()
                button_state["clear_requested"] = False
                log.info("Display cleared via button")

            force = button_state["force_refresh_once"] or bool(FORCE_REFRESH)
            if hasattr(display, "saturation"):
                display.saturation = button_state["saturation"]
            diag_state.button_saturation = button_state["saturation"]
        else:
            force = bool(FORCE_REFRESH)

        png, etag = fetcher.fetch(
            width=DISPLAY_WIDTH,
            height=DISPLAY_HEIGHT,
            hours=LOOKBACK_HOURS,
            refresh=1 if force else 0,
            skip_etag=first_poll,
        )
        first_poll = False
        now = time.time()
        diag_state.last_fetch_time = now
        diag_state.last_fetch_status = fetcher.last_status_code
        diag_state.collage_reachable = fetcher.last_status_code is not None

        if button_state is not None:
            button_state["force_refresh_once"] = False

        if png is not None:
            _save_diagnostic_original(png, cache_dir)
            diag_state.last_original_path = os.path.join(cache_dir, "last-original.png")

            png = overlay_timestamp(png)

            display.show(png)

            _save_diagnostic_quantized(display, cache_dir)
            diag_state.last_quantized_path = os.path.join(cache_dir, "last-quantized.png")
            diag_state.last_etag = etag
            diag_state.last_served_at = now
            if etag:
                fetcher.save_etag(etag)
        else:
            log.debug("Skipping display update (no new data)")

        if button_state is not None:
            button_state["wake_event"].wait(timeout=POLL_INTERVAL)
            button_state["wake_event"].clear()
        else:
            time.sleep(POLL_INTERVAL)


def main():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    global _display, _diag_state
    _display = create_display(DISPLAY_DRIVER, saturation=SATURATION)

    _diag_state.display_driver = DISPLAY_DRIVER
    _diag_state.display_resolution = _display.resolution
    _diag_state.display_saturation = SATURATION
    _diag_state.collage_url = COLLAGE_URL
    _diag_state.poll_interval = POLL_INTERVAL
    _diag_state.lookback_hours = LOOKBACK_HOURS
    _diag_state.force_refresh = bool(FORCE_REFRESH)

    if DIAGNOSTICS_PORT > 0:
        server = DiagnosticsServer(
            _diag_state, CACHE_DIR, port=DIAGNOSTICS_PORT
        )
        server.start()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    fetcher = CollageFetcher(COLLAGE_URL, cache_dir=CACHE_DIR)

    button_state = None
    if BUTTONS_ENABLED:
        button_state = {
            "wake_event": threading.Event(),
            "force_refresh_once": False,
            "clear_requested": False,
            "saturation": SATURATION,
        }
        try:
            from .buttons import ButtonMonitor
            ButtonMonitor(button_state).start()
            log.info("Button monitor enabled")
        except Exception as e:
            log.warning("Button monitor failed to start: %s", e)
            button_state = None

    log.info(
        "Starting birdnet-collage-eink: %s → %s every %ds (lookback=%dh, refresh=%d, saturation=%.2f, buttons=%s)",
        COLLAGE_URL, DISPLAY_DRIVER, POLL_INTERVAL, LOOKBACK_HOURS, FORCE_REFRESH,
        SATURATION, "yes" if button_state else "no",
    )

    _poll_loop(_display, fetcher, _diag_state, CACHE_DIR, button_state=button_state)


if __name__ == "__main__":
    main()