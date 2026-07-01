#!/usr/bin/env bash
# birdnet-collage-eink: one-shot Pi Zero setup
set -euo pipefail

REPO_DIR="/opt/birdnet-collage-eink"
VENV_DIR="$HOME/.virtualenvs/pimoroni"
SERVICE="birdnet-eink"

echo "==> Installing system packages..."
sudo apt update && sudo apt install -y python3-pip python3-venv

echo "==> Enabling SPI and I2C..."
sudo raspi-config nonint do_spi 0 || true
sudo raspi-config nonint do_i2c 0 || true

# Disable SPI chip-select to avoid conflict with Inky
CONFIG_FILE="/boot/firmware/config.txt"
if [ -f "$CONFIG_FILE" ]; then
    if ! grep -q "dtoverlay=spi0-0cs" "$CONFIG_FILE"; then
        echo "dtoverlay=spi0-0cs" | sudo tee -a "$CONFIG_FILE"
        echo "  -> Added dtoverlay=spi0-0cs (reboot required)"
    fi
fi

echo "==> Creating venv..."
mkdir -p "$VENV_DIR"
python3 -m venv --system-site-packages "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "==> Installing Python packages..."
pip install --upgrade pip
pip install requests Pillow inky

echo "==> Setting up repo..."
sudo mkdir -p "$REPO_DIR"
sudo chown "$USER:$USER" "$REPO_DIR"
# rsync is done by opencode /deploy command — this script assumes
# the repo has already been copied to $REPO_DIR

echo "==> Installing systemd service..."
sudo cp "$REPO_DIR/deploy/birdnet-eink.service" /etc/systemd/system/
sudo sed -i "s/User=pi/User=$USER/; s/Group=pi/Group=$USER/" /etc/systemd/system/birdnet-eink.service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"

echo ""
echo "==> Done! Reboot to apply SPI overlay, then:"
echo "    sudo systemctl start $SERVICE"
echo "    journalctl -u $SERVICE --no-pager -n 50"