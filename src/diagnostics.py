import datetime
import json
import logging
import os
import platform
import shutil
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import dataclass, field

from . import __version__

log = logging.getLogger(__name__)

_SYSTEM_INFO_CACHE = {}
_SYSTEM_INFO_TTL = 10


@dataclass
class DiagnosticsState:
    version: str = __version__
    process_start_time: float = field(default_factory=time.time)
    display_driver: str = ""
    display_resolution: tuple = (1600, 1200)
    display_saturation: float = 0.5
    collage_url: str = ""
    poll_interval: int = 300
    lookback_hours: int = 24
    force_refresh: bool = False
    last_etag: str | None = None
    last_served_at: float | None = None
    last_original_path: str | None = None
    last_quantized_path: str | None = None
    last_fetch_status: int | None = None
    last_fetch_time: float | None = None
    collage_reachable: bool = True


def _ts(secs):
    if secs is None:
        return None
    return datetime.datetime.fromtimestamp(secs, tz=datetime.timezone.utc).isoformat()


def collect_system_info(cache_dir):
    now = time.time()
    cached = _SYSTEM_INFO_CACHE.get("info")
    cached_at = _SYSTEM_INFO_CACHE.get("at", 0)
    if cached is not None and now - cached_at < _SYSTEM_INFO_TTL:
        return cached

    info = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }

    cpu_temp = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            cpu_temp = round(int(f.read().strip()) / 1000, 1)
    except (FileNotFoundError, OSError, ValueError):
        pass
    info["cpu_temp_celsius"] = cpu_temp

    mem_total = mem_avail = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    mem_avail = int(line.split()[1]) // 1024
    except (FileNotFoundError, OSError, ValueError):
        pass
    info["memory_total_mb"] = mem_total
    info["memory_available_mb"] = mem_avail
    info["memory_percent"] = (
        round(100 * (mem_total - mem_avail) / mem_total, 1)
        if mem_total and mem_avail
        else None
    )

    disk = None
    try:
        du = shutil.disk_usage(cache_dir)
        one_gb = 1024 ** 3
        disk = {
            "total_gb": round(du.total / one_gb, 1),
            "used_gb": round(du.used / one_gb, 1),
            "free_gb": round(du.free / one_gb, 1),
            "percent": round(100 * du.used / du.total, 1),
        }
    except OSError:
        pass
    info["disk"] = disk

    _SYSTEM_INFO_CACHE["info"] = info
    _SYSTEM_INFO_CACHE["at"] = now
    return info


class DiagnosticsHandler(BaseHTTPRequestHandler):
    state: DiagnosticsState = None
    cache_dir: str = ""

    def do_GET(self) -> None:
        if self.path == "/diagnostics":
            self._serve_json()
        elif self.path == "/diagnostics/last-image":
            self._serve_file(self.state.last_original_path)
        elif self.path == "/diagnostics/last-image/quantized":
            self._serve_file(self.state.last_quantized_path)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_json(self) -> None:
        st = self.state
        uptime = time.time() - st.process_start_time
        body = json.dumps(
            {
                "version": st.version,
                "service": "birdnet-eink",
                "process_start_time": _ts(st.process_start_time),
                "uptime_seconds": round(uptime, 1),
                "display": {
                    "driver": st.display_driver,
                    "resolution": list(st.display_resolution),
                    "saturation": st.display_saturation,
                },
                "poll": {
                    "collage_url": st.collage_url,
                    "poll_interval_seconds": st.poll_interval,
                    "lookback_hours": st.lookback_hours,
                    "force_refresh": st.force_refresh,
                },
                "connectivity": {
                    "collage_reachable": st.collage_reachable,
                    "last_fetch_status": st.last_fetch_status,
                    "last_fetch_time": _ts(st.last_fetch_time),
                },
                "last_image": {
                    "etag": st.last_etag,
                    "served_at": _ts(st.last_served_at),
                    "original_url": (
                        "/diagnostics/last-image"
                        if st.last_original_path
                        else None
                    ),
                    "quantized_url": (
                        "/diagnostics/last-image/quantized"
                        if st.last_quantized_path
                        else None
                    ),
                },
                "system": collect_system_info(self.cache_dir),
            },
            indent=2,
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: str | None) -> None:
        if not path or not os.path.isfile(path):
            self.send_response(204)
            self.end_headers()
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self.send_response(500)
            self.end_headers()

    def log_message(self, fmt, *args) -> None:
        log.debug("diagnostics: %s", fmt % args)


class DiagnosticsServer:
    def __init__(
        self,
        state: DiagnosticsState,
        cache_dir: str,
        host: str = "0.0.0.0",
        port: int = 8082,
    ) -> None:
        self._state = state
        self._cache_dir = cache_dir
        self._host = host
        self._port = port
        self._server = None
        self._thread = None

    def start(self) -> None:
        DiagnosticsHandler.state = self._state
        DiagnosticsHandler.cache_dir = self._cache_dir
        try:
            self._server = HTTPServer((self._host, self._port), DiagnosticsHandler)
            self._server.timeout = 0.5
            self._thread = threading.Thread(
                target=self._server.serve_forever, daemon=True
            )
            self._thread.start()
            log.info(
                "Diagnostics server listening on http://%s:%d",
                self._host,
                self.server_port,
            )
        except OSError as e:
            log.warning("Diagnostics server failed to start on %d: %s", self._port, e)
            self._server = None

    @property
    def server_port(self) -> int | None:
        return self._server.server_port if self._server is not None else None

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
