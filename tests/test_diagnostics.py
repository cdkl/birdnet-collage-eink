import json
import os
import urllib.request

import pytest

from src.diagnostics import DiagnosticsState, DiagnosticsServer, collect_system_info


@pytest.fixture
def state():
    return DiagnosticsState()


@pytest.fixture
def server(state, tmp_path):
    s = DiagnosticsServer(state, str(tmp_path), port=0)
    s.start()
    yield s
    s.stop()


def _fetch_json(url):
    with urllib.request.urlopen(url) as resp:
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "application/json"
        return json.loads(resp.read().decode())


def test_diagnostics_json_structure(server):
    data = _fetch_json(f"http://127.0.0.1:{server.server_port}/diagnostics")

    assert data["version"] == "0.1.0"
    assert data["service"] == "birdnet-eink"
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["process_start_time"] is not None

    display = data["display"]
    assert "driver" in display
    assert isinstance(display["resolution"], list)
    assert len(display["resolution"]) == 2

    poll = data["poll"]
    assert "collage_url" in poll
    assert "poll_interval_seconds" in poll

    conn = data["connectivity"]
    assert conn["collage_reachable"] is True
    assert conn["last_fetch_status"] is None

    img = data["last_image"]
    assert img["etag"] is None
    assert img["original_url"] is None
    assert img["quantized_url"] is None

    sys_info = data["system"]
    assert "hostname" in sys_info
    assert "platform" in sys_info
    assert "python_version" in sys_info
    assert "cpu_temp_celsius" in sys_info
    assert "memory_percent" in sys_info
    assert "disk" in sys_info


def test_diagnostics_last_image_204(server):
    port = server.server_port
    url = f"http://127.0.0.1:{port}/diagnostics/last-image"
    with urllib.request.urlopen(url) as resp:
        assert resp.status == 204

    url = f"http://127.0.0.1:{port}/diagnostics/last-image/quantized"
    with urllib.request.urlopen(url) as resp:
        assert resp.status == 204


def test_diagnostics_last_image_200(server, tmp_path, state):
    png_path = os.path.join(tmp_path, "last-original.png")
    with open(png_path, "wb") as f:
        f.write(b"\x89PNG_TEST")
    state.last_original_path = png_path

    port = server.server_port
    url = f"http://127.0.0.1:{port}/diagnostics/last-image"
    with urllib.request.urlopen(url) as resp:
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "image/png"
        assert resp.read() == b"\x89PNG_TEST"


def test_diagnostics_quantized_200(server, tmp_path, state):
    q_path = os.path.join(tmp_path, "last-quantized.png")
    with open(q_path, "wb") as f:
        f.write(b"\x89PNG_QUANT")
    state.last_quantized_path = q_path

    port = server.server_port
    url = f"http://127.0.0.1:{port}/diagnostics/last-image/quantized"
    with urllib.request.urlopen(url) as resp:
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "image/png"
        assert resp.read() == b"\x89PNG_QUANT"


def test_diagnostics_404(server):
    port = server.server_port
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/nonexistent")
    assert exc.value.code == 404


def test_diagnostics_state_updates(server, state):
    port = server.server_port
    state.last_etag = "etag42"
    state.last_served_at = 1000.0
    state.last_fetch_status = 200
    state.last_fetch_time = 1000.0
    state.last_original_path = "/tmp/fake.png"
    state.last_quantized_path = "/tmp/fake_q.png"
    state.collage_reachable = True

    data = _fetch_json(f"http://127.0.0.1:{port}/diagnostics")
    assert data["last_image"]["etag"] == "etag42"
    assert data["last_image"]["original_url"] is not None
    assert data["last_image"]["quantized_url"] is not None
    assert data["connectivity"]["last_fetch_status"] == 200
    assert data["connectivity"]["collage_reachable"] is True


def test_diagnostics_system_info_fallback(tmp_path):
    info = collect_system_info(str(tmp_path))
    assert info["hostname"] is not None
    assert info["platform"] is not None
    assert info["python_version"] is not None
    assert "cpu_temp_celsius" in info
    assert "memory_percent" in info
    assert "disk" in info
