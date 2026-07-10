#!/usr/bin/env bash
# birdnet-collage-eink: rsync repo to Pi, update systemd unit, restart service.
set -euo pipefail

PI_USER="${1:-${PI_USER:-}}"
PI_HOST="${2:-${PI_HOST:-}}"
if [ -z "$PI_USER" ] || [ -z "$PI_HOST" ]; then
    echo "Usage: deploy.sh <PI_USER> <PI_HOST>"
    echo "  or set PI_USER and PI_HOST env vars" >&2
    exit 1
fi

REPO_DIR="/opt/birdnet-collage-eink"
SERVICE_FILE="$REPO_DIR/deploy/birdnet-eink.service"
UNIT_PATH="/etc/systemd/system/birdnet-eink.service"

echo "==> Rsyncing to $PI_USER@$PI_HOST:$REPO_DIR"
rsync -az --delete \
    --exclude __pycache__ \
    --exclude .git \
    --exclude '*.pyc' \
    --exclude .pytest_cache \
    --exclude .env \
    --exclude shutdown.png \
    . "$PI_USER@$PI_HOST:$REPO_DIR/"

echo "==> Updating systemd unit on $PI_HOST"
ssh "$PI_USER@$PI_HOST" "
    sudo cp '$SERVICE_FILE' '$UNIT_PATH' &&
    sudo sed -i 's/User=pi/User=$PI_USER/; s/Group=pi/Group=$PI_USER/' '$UNIT_PATH' &&
    sudo sed -i \"s|ExecStart=%h/.virtualenvs/pimoroni/bin/python3|ExecStart=/home/$PI_USER/.virtualenvs/pimoroni/bin/python3|\" '$UNIT_PATH' &&
    sudo systemctl daemon-reload &&
    sudo systemctl restart birdnet-eink
"

sleep 2
echo "==> Recent logs"
ssh "$PI_USER@$PI_HOST" 'journalctl -u birdnet-eink --no-pager -n 30'
