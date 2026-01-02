#!/usr/bin/env python3
"""
noVNC Keyboard Agent
WebSocket server that monitors text field focus and sends show/hide signals
"""

import asyncio
import json
import signal
import sys
import os
import logging
from pathlib import Path

import yaml

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    os.system('pip3 install websockets --break-system-packages -q')
    import websockets

from focus_detector import FocusDetector, check_dependencies, install_dependencies


class KeyboardAgent:
    def __init__(self, config_path=None):
        """Initialize the keyboard agent"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        self.detector = FocusDetector(config_path)
        self.clients = set()
        self.running = False
        self.last_state = None
        
        # Server settings
        self.host = self.config.get('server', {}).get('host', '0.0.0.0')
        self.port = self.config.get('server', {}).get('port', 6082)
        self.poll_interval = self.config.get('detection', {}).get('poll_interval', 100) / 1000
        
        self.logger.info(f"Agent initialized - {self.host}:{self.port}")
    
    def _load_config(self, config_path):
        """Load configuration from yaml file"""
        if config_path is None:
            config_path = Path.home() / ".config" / "novnc-keyboard" / "config.yaml"
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._default_config()
    
    def _default_config(self):
        """Return default configuration"""
        return {
            'server': {
                'host': '0.0.0.0',
                'port': 6082
            },
            'detection': {
                'poll_interval': 100
            },
            'logging': {
                'level': 'info',
                'file': '~/.config/novnc-keyboard/agent.log'
            }
        }
    
    def setup_logging(self):
        """Setup logging"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'info').upper())
        log_file = os.path.expanduser(log_config.get('file', '~/.config/novnc-keyboard/agent.log'))
        
        # Create log directory if needed
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger('KeyboardAgent')
        self.logger.setLevel(log_level)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    async def register(self, websocket):
        """Register a new client connection"""
        self.clients.add(websocket)
        client_ip = websocket.remote_address[0] if websocket.remote_address else 'unknown'
        self.logger.info(f"Client connected: {client_ip} (total: {len(self.clients)})")
        
        # Send current state to new client
        if self.last_state is not None:
            await self.send_to_client(websocket, self.last_state)
    
    async def unregister(self, websocket):
        """Unregister a client connection"""
        self.clients.discard(websocket)
        client_ip = websocket.remote_address[0] if websocket.remote_address else 'unknown'
        self.logger.info(f"Client disconnected: {client_ip} (total: {len(self.clients)})")
    
    async def send_to_client(self, websocket, message):
        """Send message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            pass
    
    async def broadcast(self, message):
        """Send message to all connected clients"""
        if self.clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_client(self, websocket, path=None):
        """Handle a client WebSocket connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # Handle incoming messages from client (if needed in future)
                try:
                    data = json.loads(message)
                    self.logger.debug(f"Received from client: {data}")
                    
                    # Handle ping/pong for connection keep-alive
                    if data.get('type') == 'ping':
                        await self.send_to_client(websocket, {'type': 'pong'})
                    
                    # Handle theme info from client
                    elif data.get('type') == 'theme':
                        self.logger.info(f"Client theme: {data.get('theme')}")
                    
                    # Handle device info from client
                    elif data.get('type') == 'device':
                        self.logger.info(f"Client device: {data.get('device')}")
                    
                    # Handle key press from keyboard
                    elif data.get('type') == 'key':
                        key = data.get('key')
                        if key:
                            self.type_key(key)
                    
                    # Handle special key press
                    elif data.get('type') == 'special':
                        key = data.get('key')
                        if key:
                            self.type_special(key)
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON received: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def focus_monitor(self):
        """Monitor focus changes and broadcast to clients"""
        self.logger.info("Focus monitor started")
        
        while self.running:
            try:
                # Get current focus state
                is_focused = self.detector.is_text_field_focused()
                
                # Create state message
                current_state = {
                    'action': 'show_keyboard' if is_focused else 'hide_keyboard',
                    'focused': is_focused
                }
                
                # Only broadcast if state changed
                if self.last_state is None or self.last_state['focused'] != is_focused:
                    self.logger.info(f"Focus changed: {current_state['action']}")
                    await self.broadcast(current_state)
                    self.last_state = current_state
                
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Focus monitor error: {e}")
                await asyncio.sleep(1)
    
    async def start_server(self):
        """Start the WebSocket server"""
        self.running = True
        
        # Start focus monitor
        monitor_task = asyncio.create_task(self.focus_monitor())
        
        # Start WebSocket server
        self.logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        
        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        ):
            self.logger.info("Server is running. Press Ctrl+C to stop.")
            
            # Keep running until stopped
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                pass
        
        self.running = False
        monitor_task.cancel()
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        self.logger.info("Agent stopping...")
    
    def type_key(self, char):
        """Type a character using xdotool"""
        try:
            import subprocess
            # Use xdotool to type the character
            subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', '--', char],
                check=False,
                timeout=1
            )
            self.logger.debug(f"Typed: {char}")
        except Exception as e:
            self.logger.error(f"Error typing key: {e}")
    
    def type_special(self, key):
        """Type a special key using xdotool"""
        try:
            import subprocess
            # Map special keys to xdotool key names
            key_map = {
                'BackSpace': 'BackSpace',
                'Return': 'Return',
                'space': 'space',
                'Tab': 'Tab',
                'Escape': 'Escape',
                'Delete': 'Delete',
                'Left': 'Left',
                'Right': 'Right',
                'Up': 'Up',
                'Down': 'Down'
            }
            
            xdo_key = key_map.get(key, key)
            subprocess.run(
                ['xdotool', 'key', '--clearmodifiers', xdo_key],
                check=False,
                timeout=1
            )
            self.logger.debug(f"Typed special: {xdo_key}")
        except Exception as e:
            self.logger.error(f"Error typing special key: {e}")


def print_banner():
    """Print startup banner"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║             noVNC Keyboard Agent v1.0                     ║
║                                                           ║
║   Monitors text field focus and signals keyboard overlay  ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    print_banner()
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        response = input("Install them now? (y/n): ")
        if response.lower() == 'y':
            if not install_dependencies():
                sys.exit(1)
        else:
            print("Cannot continue without dependencies.")
            sys.exit(1)
    
    # Check DISPLAY
    if not os.environ.get('DISPLAY'):
        print("⚠️  DISPLAY not set. Setting to :1.0")
        os.environ['DISPLAY'] = ':1.0'
    
    # Create agent
    agent = KeyboardAgent()
    
    # Handle shutdown
    def shutdown(sig, frame):
        print("\n")
        agent.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # Run server
    try:
        asyncio.run(agent.start_server())
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    main()
