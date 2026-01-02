#!/usr/bin/env python3
"""
noVNC Keyboard - Multi-User Server Startup
"""

import sys
import signal
import argparse

# Add parent directory to path
sys.path.insert(0, '/home/ubuntu/novnc-keyboard/ubuntu-agent')

from admin_panel import set_server_config, AdminServer, ADMIN_PORT
from session_manager import get_session_manager

def main():
    parser = argparse.ArgumentParser(description='noVNC Keyboard Multi-User Server')
    parser.add_argument('--url', type=str, default='', help='Target URL (e.g., https://gmail.com)')
    parser.add_argument('--vnc', type=str, default='vnc_lite.html', help='VNC file (vnc.html or vnc_lite.html)')
    args = parser.parse_args()
    
    print("=" * 50)
    print("  noVNC Keyboard - Multi-User Server")
    print("=" * 50)
    print()
    
    # Set config
    set_server_config(url=args.url, vnc_file=args.vnc)
    print(f"  URL: {args.url if args.url else '(blank page)'}")
    print(f"  VNC: {args.vnc}")
    print()
    
    # Start session manager (singleton)
    manager = get_session_manager()
    manager.start()
    print("  ✓ Session manager started")
    
    # Start admin server
    server = AdminServer()
    server.start()
    print(f"  ✓ Admin panel on port {ADMIN_PORT}")
    print()
    print("=" * 50)
    print(f"  Admin:   http://0.0.0.0:{ADMIN_PORT}/admin")
    print(f"  Connect: http://0.0.0.0:{ADMIN_PORT}/connect")
    print("=" * 50)
    print()
    print("  Press Ctrl+C to stop")
    print()
    
    # Handle shutdown
    def shutdown(sig, frame):
        print("\n  Stopping...")
        server.stop()
        manager.stop()
        print("  ✓ Stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # Keep running
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
