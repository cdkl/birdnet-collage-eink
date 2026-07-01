import pytest
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class MockCollageHandler(BaseHTTPRequestHandler):
    _last_path = None

    def do_GET(self):
        self.__class__._last_path = self.path
        if self.path.startswith("/api/eink"):
            client_etag = self.headers.get("If-None-Match", "").strip('"')
            if client_etag == "abc123":
                self.send_response(304)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("ETag", '"abc123"')
            self.end_headers()
            self.wfile.write(b"PNG_DATA")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture
def mock_server():
    MockCollageHandler._last_path = None
    server = HTTPServer(("127.0.0.1", 0), MockCollageHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def test_fetch_200(mock_server, temp_cache):
    from src.fetcher import CollageFetcher
    port = mock_server.server_port
    fetcher = CollageFetcher(f"http://127.0.0.1:{port}", cache_dir=temp_cache)
    png, etag = fetcher.fetch()
    assert png == b"PNG_DATA"
    assert etag == "abc123"
    assert "refresh=1" not in MockCollageHandler._last_path


def test_fetch_refresh_off(mock_server, temp_cache):
    from src.fetcher import CollageFetcher
    port = mock_server.server_port
    fetcher = CollageFetcher(f"http://127.0.0.1:{port}", cache_dir=temp_cache)
    png, etag = fetcher.fetch(refresh=0)
    assert "refresh" not in MockCollageHandler._last_path


def test_fetch_refresh_on(mock_server, temp_cache):
    from src.fetcher import CollageFetcher
    port = mock_server.server_port
    fetcher = CollageFetcher(f"http://127.0.0.1:{port}", cache_dir=temp_cache)
    png, etag = fetcher.fetch(refresh=1)
    assert "refresh=1" in MockCollageHandler._last_path


def test_fetch_304(mock_server, temp_cache):
    from src.fetcher import CollageFetcher
    import os
    etag_path = os.path.join(temp_cache, "last-etag.txt")
    with open(etag_path, "w") as f:
        f.write("abc123")
    port = mock_server.server_port
    fetcher = CollageFetcher(f"http://127.0.0.1:{port}", cache_dir=temp_cache)
    png, etag = fetcher.fetch()
    assert png is None
    assert etag == "abc123"


def test_save_and_load_etag(temp_cache):
    from src.fetcher import CollageFetcher
    fetcher = CollageFetcher("http://example.com", cache_dir=temp_cache)
    fetcher.save_etag("xyz789")
    assert fetcher._load_etag() == "xyz789"


def test_fetch_timeout(temp_cache):
    from src.fetcher import CollageFetcher
    fetcher = CollageFetcher(
        "http://192.0.2.1:9999", cache_dir=temp_cache, timeout=0.1
    )
    png, etag = fetcher.fetch()
    assert png is None
    assert etag is None


def test_fetch_unexpected_status(temp_cache):
    from src.fetcher import CollageFetcher
    import os

    class FailHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(503)
            self.end_headers()

        def log_message(self, *a):
            pass

    from http.server import HTTPServer
    import threading
    server = HTTPServer(("127.0.0.1", 0), FailHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_port
        fetcher = CollageFetcher(
            f"http://127.0.0.1:{port}", cache_dir=temp_cache
        )
        png, etag = fetcher.fetch()
        assert png is None
        assert etag is None
    finally:
        server.shutdown()