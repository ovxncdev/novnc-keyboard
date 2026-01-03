#!/bin/bash
# noVNC Keyboard System - Quick Install Script

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  ⌨️  noVNC Keyboard System - Installer                 ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run without sudo (script will ask for sudo when needed)"
    exit 1
fi

# Install dependencies
echo "[1/5] Installing dependencies..."
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-websockets \
    tigervnc-standalone-server \
    tigervnc-common \
    websockify \
    novnc \
    xdotool \
    x11-utils \
    python3-gi \
    gir1.2-atspi-2.0 \
    at-spi2-core \
    unclutter \
    google-chrome-stable || true

# Create config directory
echo "[2/5] Creating config directory..."
mkdir -p ~/.config/novnc-keyboard/chrome-profiles

# Copy files
echo "[3/5] Copying files..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR"/*.py ~/.config/novnc-keyboard/ 2>/dev/null || true

# Install systemd service
echo "[4/5] Installing systemd service..."
sudo cp "$SCRIPT_DIR/novnc-keyboard.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable novnc-keyboard

# Set permissions
echo "[5/5] Setting permissions..."
chmod +x "$SCRIPT_DIR/ubuntu-agent/launcher.py" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/ubuntu-agent/start_server.py" 2>/dev/null || true

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║  ✓ Installation Complete!                             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "To start the server:"
echo "  cd $SCRIPT_DIR"
echo "  python3 launcher.py"
echo ""
echo "Or use systemd:"
echo "  sudo systemctl start novnc-keyboard"
echo ""
echo "Required AWS ports: 6080-6090, 6101-6110"
echo ""
