# birdnet-collage-eink — Specification

## Purpose

A Raspberry Pi Zero companion client for [birdnet-collage](https://github.com/your-org/birdnet-collage).
Fetches a pre-rendered bird-detection collage PNG from the `/api/eink` endpoint
and displays it on a **Pimoroni Inky Impression 13.3"** e-ink panel. Runs
headlessly as a systemd service with an infinite polling loop.

Downstream dependency: birdnet-collage (the server). This project depends on no
code from that repository — only on its HTTP API contract at `/api/eink`.

## Requirements

- **R1**: Run on a Raspberry Pi Zero (ARMv6, 32-bit, 512 MB RAM).
- **R2**: Poll birdnet-collage `/api/eink?w=N&h=N&hours=N` at a configurable interval.
- **R3**: Support ETag-based conditional GETs (`If-None-Match` → 304) to avoid unnecessary e-ink refreshes.
- **R4**: Persist the last known ETag to a file so the optimization survives service restart.
- **R5**: Drive a Pimoroni Inky Impression 13.3" e-ink display (1600×1200, 7-colour Spectra 6).
- **R6**: Support a simulator driver that writes fetched PNGs to disk (no hardware needed for development).
- **R7**: Clean the display on graceful shutdown (SIGTERM/SIGINT).
- **R8**: Restart automatically on failure (systemd `Restart=on-failure`).
- **R9**: All configuration via environment variables.
- **R10**: Pure Python dependencies only — no C-extensions that aren't pre-built for armv6l.

## Architecture

```
birdnet-collage (server)        Raspberry Pi Zero (this app)
┌──────────────────────┐        ┌──────────────────────────┐
│  /api/eink           │  HTTP  │  main.py (poll loop)     │
│  ?w=1600&h=1200      │◄──────│  ┌──────────────────┐    │
│  &hours=24           │        │  │ CollageFetcher   │    │
│                      │  304   │  │  GET /api/eink   │    │
│  If-None-Match → 304 │──────►│  │  If-None-Match   │    │
│                      │        │  │  save_etag()    │    │
│  200 image/png       │  200   │  └──────┬───────────┘    │
│  + ETag header       │──────►│         │                 │
└──────────────────────┘        │  ┌──────▼───────────┐    │
                                │  │ Display driver   │    │
                                │  │  BaseDisplay     │    │
                                │  │  ├─ InkyImpression│    │
                                │  │  └─ Simulator    │    │
                                │  └──────────────────┘    │
                                └──────────────────────────┘
```

**Stack**: Python 3.9+ → requests (HTTP) → Pillow (image processing) → inky (e-ink driver). Runs as a systemd `Type=simple` service. No web server, no frameworks.

## Key decisions

| Decision | Rationale |
|---|---|
| Pure Python, no compilation | Pi Zero is ARMv6; C-extensions must be pre-built for piwheels. `inky` ships as a platform-agnostic wheel |
| Polling loop (not push) | birdnet-collage has no websocket/pubsub. Polling with ETag caching is the lightest approach for a headless Pi |
| ETag persistence to file | Survives service restarts. Without it, every reboot triggers a full e-ink refresh unnecessarily |
| Display driver as pluggable abstract class | Swap Inky Impression ↔ simulator with one env var. Simulator enables testing on any machine |
| Inky Impression 13.3" (1600×1200) | Matches birdnet-collage `/api/eink` default resolution exactly — no rescaling needed |
| 7-colour Spectra 6 palette | Display supports Black, White, Red, Yellow, Blue, Green, Orange. PNG is quantized to 7 colours client-side |
| systemd `Restart=on-failure` | Pi Zero runs headless; service must self-heal (WiFi drop, server restart, etc.) |
| `stdout` logging → journald | Zero-config logging; no log files to rotate |
| Graceful shutdown via signal handler | SIGTERM/SIGINT → `display.clear()` → exit. Leaves display blank instead of frozen on last frame |
| `from inky.auto import auto` | Inky auto-detects the display from EEPROM — no manual model selection |
| Inky driver installed into `~/.virtualenvs/pimoroni/` | Pimoroni's recommended install path; systemd `ExecStart` points to this venv's python3 |
| SPI + I2C + `dtoverlay=spi0-0cs` required | Inky Impression uses SPI for data, I2C for EEPROM detection. Chip-select overlay needed to avoid kernel conflict |

## Display driver contract

Every driver implements `BaseDisplay`:

```python
class BaseDisplay(abc.ABC):
    @property
    def resolution(self) -> tuple[int, int]: ...

    def show(self, png_bytes: bytes) -> None: ...

    def clear(self) -> None: ...
```

### InkyImpression

- Uses `inky.auto` for automatic board detection from EEPROM.
- Converts input PNG to a paletted (P-mode) image with 7 colours (Spectra 6 palette) via `Image.ADAPTIVE`.
- Calls `set_image()`, `set_border(WHITE)`, `show()`.
- `clear()` fills with white pixels and pushes to display.

### Simulator

- Writes incoming PNG bytes to `{outdir}/eink-{count:04d}.png`.
- `clear()` is a no-op (logs only).
- Default outdir: `/tmp/eink-sim`.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `COLLAGE_URL` | `http://localhost:8081` | birdnet-collage base URL (no trailing slash) |
| `DISPLAY_DRIVER` | `simulator` | `simulator` or `inky_impression` |
| `DISPLAY_WIDTH` | `1600` | e-ink panel width in pixels |
| `DISPLAY_HEIGHT` | `1200` | e-ink panel height in pixels |
| `DISPLAY_ROTATION` | `0` | display rotation (0/90/180/270; passed to `auto()`) |
| `POLL_INTERVAL` | `300` | seconds between polls (min 60 recommended) |
| `LOOKBACK_HOURS` | `24` | detection time window passed to `/api/eink?hours=N` |
| `CACHE_DIR` | `/var/lib/birdnet-eink` | directory for `last-etag.txt` |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose HTTP tracing |
| `SIMULATOR_OUTDIR` | `/tmp/eink-sim` | output directory for simulator driver |
| `FORCE_REFRESH` | `0` | append `&refresh=1` to force regeneration on every poll |
| `SATURATION` | `0.5` | colour saturation for 7-colour quantization (0.0–1.0) |
| `DIAGNOSTICS_PORT` | `8082` | port for built-in diagnostics HTTP server (0 to disable) |

**Constraint**: Every env var consumed by the application must appear in:
1. `src/main.py` — Python-side default and `os.getenv()` call.
2. `.env.example` — documents the variable for users.

## API contract (with birdnet-collage)

The app calls exactly one endpoint:

**`GET /api/eink?w={width}&h={height}&hours={hours}[&refresh=1]`**

| Request header | Value | When |
|---|---|---|
| `If-None-Match` | `"<etag>"` | On polls after the first successful fetch |

| Response | Body | Headers | Meaning |
|---|---|---|---|
| 200 | PNG bytes | `ETag: "<hash>"` | New collage — display it |
| 304 | (empty) | — | No change — skip update |
| 503 | (empty) | — | Server unavailable — log and retry |

ETag is a SHA-256 hash of `sorted(sci + n + last_seen tuples) + hours + version`.
Algorithm defined in birdnet-collage `src/collage_renderer.py:compute_etag()`.

## Dependencies

```
requests>=2.32      HTTP client
Pillow>=11.0        Image processing (open PNG, palette conversion)
inky>=2.1.0         Pimoroni Inky e-ink display driver (2.1.0+ has Spectra 13.3" support)
```

`inky` is an optional dependency — the simulator driver works without it.
`inky` install does not require compilation (pure Python + bundled firmware blobs).

## Inky Impression 13.3" specific details

- **Model**: Pimoroni Inky Impression 13.3" (Spectra 6 / UC8159)
- **Resolution**: 1600 × 1200 pixels
- **Colour**: 7-colour (Black, White, Red, Yellow, Blue, Green, Orange)
- **Interface**: SPI (data) + I2C (EEPROM auto-detection)
- **Chipset**: UC8159 (7-colour)
- **Pi Zero pinout**: HAT-compatible 40-pin header

### Required Pi configuration (from `deploy/install.sh`)

1. Enable SPI: `sudo raspi-config nonint do_spi 0`
2. Enable I2C: `sudo raspi-config nonint do_i2c 0`
3. Disable SPI chip-select 0: add `dtoverlay=spi0-0cs` to `/boot/firmware/config.txt`
4. Reboot

### Driver pipeline

```
PNG bytes → PIL Image.open() → convert("RGB") → quantize(palette=inky_palette, dither=NONE)
→ inky.set_image() → inky.set_border(WHITE) → inky.show()
```

Full refresh takes ~15s on the 13.3" panel. Partial refresh is not
supported by the Spectra 6 firmware.

## Deployment

### One-time install (on the Pi)

1. Clone or rsync the repo to `/opt/birdnet-collage-eink/`.
2. Run `deploy/install.sh` — installs system packages, enables SPI/I2C, creates venv, installs deps, wires systemd service.
3. Reboot to apply `dtoverlay=spi0-0cs`.
4. `sudo systemctl start birdnet-eink`.

### systemd unit (`deploy/birdnet-eink.service`)

| Field | Value |
|---|---|
| `Type` | `simple` |
| `User`/`Group` | `$USER` (set by `deploy/install.sh` at install time) |
| `WorkingDirectory` | `/opt/birdnet-collage-eink` |
| `ExecStart` | `%h/.virtualenvs/pimoroni/bin/python3 -m src` (%h = home of `User`) |
| `Restart` | `on-failure` |
| `RestartSec` | 10 |

## Tests

20 pytest tests covering:

| File | Tests | Scope |
|---|---|---|
| `test_fetcher.py` | 5 | Mock HTTP server: 200 path, 304 path, 503 error, connection timeout, ETag persistence |
| `test_display_simulator.py` | 7 | Simulator writes PNGs, incrementing filenames, clear is no-op, resolution, unknown driver, driver registry, blend palette |
| `test_main.py` | 3 | Main loop integration, signal handler, env var defaults |
| `test_diagnostics.py` | 5 | Diagnostics JSON structure, last-image/quantized endpoints, 404, state updates |

Mocking pattern: `http.server.HTTPServer` with a `BaseHTTPRequestHandler` subclass
served in a daemon thread. No `unittest.mock` or third-party libraries required.

Run via `python3 -m pytest`. Extras needed: `pip install pytest requests Pillow`.

## Limitations

- **No partial refresh**: E-ink full refresh takes ~15s. The app does not attempt
  partial-update mode (unsupported by Spectra 6 firmware).
- **No multi-display**: One display per Pi. No daisy-chaining or multi-HAT support.
- **No dynamic resolution**: Display dimensions are hardcoded in env vars, not
  queried from the panel. Must match the Inky Impression 13.3" settings.
- **No offline mode**: If birdnet-collage is unreachable, the display stays on
  the last successfully pushed image (no fallback message). The old image
  persists because e-ink holds its state without power.
- **Simulator only on non-Pi hardware**: The `inky` library installs on macOS
  but fails at import (SPI GPIO unavailable). The driver factory catches
  `ImportError` gracefully — `inky_impression` is simply not registered on
  non-Pi machines.
- **Single-threaded polling with diagnostics thread**: The polling loop blocks on
  each `time.sleep()`. A daemon thread serves the diagnostics HTTP endpoint
  concurrently. Not an issue for headless deployment.

## Diagnostics endpoint

A built-in HTTP server listens on `DIAGNOSTICS_PORT` and serves device status
in a daemon thread alongside the polling loop.

### Endpoints

| Path | Method | Response |
|---|---|---|
| `/diagnostics` | GET | `200 application/json` — full device status (see schema below) |
| `/diagnostics/last-image` | GET | `200 image/png` — last raw PNG fetched from server (or `204` if none) |
| `/diagnostics/last-image/quantized` | GET | `200 image/png` — post-7-colour-quantization PNG (or `204` if none) |

### JSON schema (`/diagnostics`)

```json
{
  "version": "0.1.0",
  "service": "birdnet-eink",
  "process_start_time": "<ISO-8601>",
  "uptime_seconds": 12345.0,
  "display": {
    "driver": "inky_impression",
    "resolution": [1600, 1200],
    "saturation": 0.5
  },
  "poll": {
    "collage_url": "http://birdnet-collage:8081",
    "poll_interval_seconds": 300,
    "lookback_hours": 24,
    "force_refresh": false
  },
  "connectivity": {
    "collage_reachable": true,
    "last_fetch_status": 200,
    "last_fetch_time": "<ISO-8601>"
  },
  "last_image": {
    "etag": "abc123",
    "served_at": "<ISO-8601>",
    "original_url": "/diagnostics/last-image",
    "quantized_url": "/diagnostics/last-image/quantized"
  },
  "system": {
    "hostname": "birdnet-pi",
    "platform": "Linux-6.1.21-armv6l-with-glibc2.31",
    "python_version": "3.11.2",
    "cpu_temp_celsius": 42.5,
    "memory_percent": 45.6,
    "memory_total_mb": 512,
    "memory_available_mb": 278,
    "disk": {
      "total_gb": 15.0,
      "used_gb": 10.2,
      "free_gb": 4.8,
      "percent": 67.8
    }
  }
}
```

System fields (`cpu_temp_celsius`, memory, disk) return `null` on non-Linux
or when the corresponding `/proc`/`/sys` file is inaccessible.

### Image storage

Each time `display.show()` succeeds, two files are written (overwritten) to
`CACHE_DIR`:

| File | Content |
|---|---|
| `last-original.png` | Raw PNG bytes as received from the collage server |
| `last-quantized.png` | PNG after 7-colour quantization (pixel-exact match to what InkyImpression pushes to hardware) |

## Repository structure

```
birdnet-collage-eink/
├── src/
│   ├── __init__.py
│   ├── __version__           # version string (0.1.0)
│   ├── __main__.py          # python -m src entry point
│   ├── main.py              # polling loop + signal handling + diagnostics wiring
│   ├── fetcher.py           # HTTP client with ETag cache
│   ├── diagnostics.py       # DiagnosticsServer + state + system info collection
│   └── display/
│       ├── __init__.py      # factory: create_display(name)
│       ├── base.py          # abstract BaseDisplay
│       ├── inky_impression.py  # real hardware driver
│       └── simulator.py     # writes PNGs to disk
├── tests/
│   ├── conftest.py
│   ├── test_fetcher.py
│   ├── test_main.py
│   ├── test_display_simulator.py
│   └── test_diagnostics.py
├── deploy/
│   ├── birdnet-eink.service   # systemd unit
│   └── install.sh             # one-shot Pi setup
├── opencode.json              # /deploy, /logs, /status, /simulate commands
├── AGENTS.md                  # agent instructions
├── .env.example               # config template (committed)
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Attribution

Display driver via [Pimoroni Inky](https://github.com/pimoroni/inky) library (MIT).
Collage images served by [birdnet-collage](https://github.com/your-org/birdnet-collage).
Detection data from Birdnet-GO / BirdNET (Cornell Lab of Ornithology).
License: MIT.