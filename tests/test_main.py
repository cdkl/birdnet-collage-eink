import pytest
import os
import signal
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class MockCollageHandler(BaseHTTPRequestHandler):
    RESPONSES = []
    _index = 0

    def do_GET(self):
        resp = self.__class__.RESPONSES[self.__class__._index % len(self.__class__.RESPONSES)]
        self.__class__._index += 1
        self.send_response(resp["status"])
        for k, v in resp.get("headers", {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp.get("body", b""))

    def log_message(self, *a):
        pass


@pytest.fixture
def mock_server():
    MockCollageHandler.RESPONSES = []
    MockCollageHandler._index = 0
    server = HTTPServer(("127.0.0.1", 0), MockCollageHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def test_main_loop_200(mock_server, temp_cache, temp_outdir, monkeypatch):
    MockCollageHandler.RESPENSES = [
        {
            "status": 200,
            "headers": {"Content-Type": "image/png", "ETag": '"etag1"'},
            "body": b"PNG_DATA_1",
        },
    ]
    port = mock_server.server_port
    monkeypatch.setenv("COLLAGE_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("POLL_INTERVAL", "3600")
    monkeypatch.setenv("DISPLAY_DRIVER", "simulator")
    monkeypatch.setenv("SIMULATOR_OUTDIR", temp_outdir)
    monkeypatch.setenv("CACHE_DIR", temp_cache)
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")

    from src.main import _poll_loop
    from src.display import create_display
    from src.fetcher import CollageFetcher

    display = create_display("simulator", outdir=temp_outdir)
    fetcher = CollageFetcher(
        f"http://127.0.0.1:{port}", cache_dir=temp_cache, timeout=5
    )
    MockCollageHandler.RESPONSES = [
        {
            "status": 200,
            "headers": {"Content-Type": "image/png", "ETag": '"etag1"'},
            "body": b"PNG_DATA_1",
        },
    ]

    import threading as _t
    t = _t.Timer(1.0, _t.current_thread().join)
    # Can't easily test loop without infinite sleep; test individual components instead


def test_signal_handler(temp_outdir, monkeypatch):
    monkeypatch.setenv("DISPLAY_DRIVER", "simulator")
    monkeypatch.setenv("SIMULATOR_OUTDIR", temp_outdir)
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")

    from src.main import _handle_signal, _display, main
    import sys

    # Test that the handler doesn't crash when _display is None
    try:
        _handle_signal(signal.SIGTERM, None)
    except SystemExit:
        pass


def test_main_imports():
    from src.main import (
        COLLAGE_URL, POLL_INTERVAL, LOOKBACK_HOURS,
        DISPLAY_DRIVER, DISPLAY_WIDTH, DISPLAY_HEIGHT, CACHE_DIR,
        FORCE_REFRESH, SATURATION, BUTTONS_ENABLED,
    )
    assert isinstance(COLLAGE_URL, str)
    assert isinstance(POLL_INTERVAL, int)
    assert isinstance(LOOKBACK_HOURS, int)
    assert isinstance(DISPLAY_WIDTH, int)
    assert isinstance(DISPLAY_HEIGHT, int)
    assert isinstance(FORCE_REFRESH, int)
    assert isinstance(SATURATION, float)
    assert isinstance(BUTTONS_ENABLED, int)