# AGENTS.md

## Project governance

`spec.md` is the authoritative record of requirements, architecture, and
constraints. Read it first when approaching any task. Update it when
requirements change, new decisions are made, or limitations are removed.

## Running the app

### One-time setup

The `opencode.json` commands for /deploy, /logs, and /status reference
shell variables `$PI_USER` and `$PI_HOST`. Set them before running opencode:

```bash
cp .env.example .env        # create personal config (already gitignored)
# edit .env: fill in PI_USER and PI_HOST (e.g. PI_HOST=birdnet-pi.local)
source .env                  # export vars into shell
```

Or add `export PI_USER=...` / `export PI_HOST=...` to `~/.zshrc`.

### Normal usage

```bash
# local testing (uses simulator driver — writes PNGs to /tmp/eink-sim/)
DISPLAY_DRIVER=simulator SIMULATOR_OUTDIR=/tmp/eink-sim \
  COLLAGE_URL=http://localhost:8081 POLL_INTERVAL=60 \
  python3 -m src

# on the Pi (via systemd)
sudo systemctl start birdnet-eink

# tests
python3 -m pytest
```

## Known values

| Item | Value |
|---|---|
| Display | Inky Impression 13.3" (1600x1200, 7-colour Spectra 6) |
| Pi hostname | `$PI_HOST` — set in `.env` (gitignored), see `.env.example` |
| Pi user | `$PI_USER` — set in `.env` (gitignored), see `.env.example` |
| Service name | `birdnet-eink` |
| Repo path on Pi | `/opt/birdnet-collage-eink` |
| Venv on Pi | `~/.virtualenvs/pimoroni/` |
| Collage server | `http://birdnet-collage:8081` |

## Key constraints

- **Pi Zero is ARMv6 (32-bit)**. All dependencies are pure Python or
  pre-compiled wheels from piwheels. No C-extensions.
- **Inky driver** uses the `inky` PyPI package with `from inky.auto import auto`.
  It auto-detects the display from EEPROM. Requires SPI + I2C enabled and
  `dtoverlay=spi0-0cs` in `/boot/firmware/config.txt`.
- **Polling loop** sleeps `POLL_INTERVAL` seconds between fetches. Uses ETag
  to skip redundant updates (saves display wear — full e-ink refresh takes ~15s).
- **No server dependency** beyond the HTTP API contract on `/api/eink`.

## Iterative workflow

1. Edit code locally
2. `python3 -m pytest` — verify simulator tests pass
3. `/simulate` — run locally against a birdnet-collage instance to verify PNG output
4. `/deploy` — rsync to Pi, restart service, tail logs
5. `/logs` — check for errors (journalctl)

## Tests

See `spec.md` § Tests for the authoritative list. Run via `python3 -m pytest`.