# birdnet-collage-eink

Raspberry Pi Zero companion app for [birdnet-collage](https://github.com/your-org/birdnet-collage).
Displays a live bird detection collage on a **Pimoroni Inky Impression 13.3"** e-ink screen.

## How it works

```
birdnet-collage (server)  ── HTTP /api/eink ──►  Pi Zero (this app)
  • Renders collage PNG           │                  │
  • Returns ETag header           │              main.py loop
  • Supports If-None-Match (304)  │           every POLL_INTERVALs
                                  │                  │
                                  │         ┌────────┴────────┐
                                  │     fetcher.py      display/
                                  │     (ETag cache)    │
                                  │                     ├── inky_impression.py (real)
                                  │                     └── simulator.py (testing)
```

The app polls `/api/eink?w=1600&h=1200&hours=24` every N seconds.
If the ETag hasn't changed, the server returns 304 and the display is
spared a full refresh. On a new collage, the PNG is quantized to the
display's 7-colour Spectra 6 palette and pushed to the panel.

## Quickstart

```bash
# install dependencies
pip install -r requirements.txt

# test locally (writes PNGs to /tmp/eink-sim/)
DISPLAY_DRIVER=simulator SIMULATOR_OUTDIR=/tmp/eink-sim \
  COLLAGE_URL=http://localhost:8081 POLL_INTERVAL=60 \
  python3 -m src

# run tests
python3 -m pytest
```

## Pi Zero installation

```bash
# copy the repo to the Pi (set $PI_USER and $PI_HOST in .env first — see .env.example)
rsync -az --exclude __pycache__ --exclude .git . $PI_USER@$PI_HOST:/opt/birdnet-collage-eink/

# SSH into the Pi and run:
cd /opt/birdnet-collage-eink
./deploy/install.sh

# Reboot, then check:
sudo systemctl start birdnet-eink
journalctl -u birdnet-eink --no-pager -n 50
```

## Configuration

All via environment variables:

| Variable | Default | Description |
|---|---|---|
| `COLLAGE_URL` | `http://localhost:8081` | birdnet-collage base URL |
| `DISPLAY_DRIVER` | `simulator` | `simulator` or `inky_impression` |
| `DISPLAY_WIDTH` | `1600` | panel width in px |
| `DISPLAY_HEIGHT` | `1200` | panel height in px |
| `DISPLAY_ROTATION` | `0` | panel rotation (0/90/180/270) |
| `POLL_INTERVAL` | `300` | seconds between polls |
| `LOOKBACK_HOURS` | `24` | detection time window |
| `CACHE_DIR` | `/var/lib/birdnet-eink` | ETag persistence directory |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose logging |
| `SIMULATOR_OUTDIR` | `/tmp/eink-sim` | output directory (simulator only) |

## Display drivers

- **inky_impression** — real hardware driver using `inky.auto`. Requires SPI,
  I2C, and `dtoverlay=spi0-0cs` on the Pi.
- **simulator** — writes fetched PNGs to disk. Useful for testing on any machine.

## Further reading

- [`spec.md`](spec.md) — full requirements, architecture, and design decisions.
- [`AGENTS.md`](AGENTS.md) — opencode agent instructions and iterative workflow.
- [`deploy/install.sh`](deploy/install.sh) — one-shot Pi setup script.

## Attribution

Display driver via [Pimoroni Inky](https://github.com/pimoroni/inky) library (MIT).
Collage images served by [birdnet-collage](https://github.com/your-org/birdnet-collage).
Detection data from Birdnet-GO / BirdNET (Cornell Lab of Ornithology).

## License

MIT