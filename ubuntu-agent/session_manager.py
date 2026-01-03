#!/usr/bin/env python3
"""
noVNC Keyboard - Session Manager
Handles multi-user sessions with auto-assignment by IP
"""

import os
import json
import time
import subprocess
import threading
import signal
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
import logging

# ============================================
# CONFIGURATION
# ============================================

CONFIG_DIR = Path.home() / ".config" / "novnc-keyboard"
SESSIONS_FILE = CONFIG_DIR / "sessions.json"
CHROME_PROFILES_DIR = Path.home() / ".config" / "novnc-keyboard" / "chrome-profiles"

# Port ranges
NOVNC_PORT_START = 6081
NOVNC_PORT_END = 6090
AGENT_PORT_START = 6101
AGENT_PORT_END = 6110
VNC_DISPLAY_START = 1
VNC_DISPLAY_END = 10
ADMIN_PORT = 6080

# Limits
MAX_CONCURRENT_SESSIONS = 10
SESSION_TIMEOUT_MINUTES = 10

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class Session:
    session_id: str
    ip_address: str
    vnc_display: int
    vnc_port: int
    novnc_port: int
    agent_port: int
    chrome_profile: str
    vnc_file: str  # vnc.html or vnc_lite.html
    created_at: str
    last_activity: str
    status: str  # active, inactive, closed
    screen_width: int = 375
    screen_height: int = 812
    user_agent: str = ''
    pid_vnc: Optional[int] = None
    pid_chrome: Optional[int] = None
    pid_agent: Optional[int] = None
    pid_websockify: Optional[int] = None

    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# ============================================
# SESSION MANAGER
# ============================================

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.ip_to_session: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.running = False
        self.cleanup_thread = None
        
        # Setup logging
        self.setup_logging()
        
        # Create directories
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CHROME_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing sessions
        self.load_sessions()
    
    def setup_logging(self):
        """Setup logging"""
        log_file = CONFIG_DIR / "session_manager.log"
        
        self.logger = logging.getLogger('SessionManager')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def load_sessions(self):
        """Load sessions from file"""
        if SESSIONS_FILE.exists():
            try:
                with open(SESSIONS_FILE, 'r') as f:
                    data = json.load(f)
                    for session_data in data.get('sessions', []):
                        session = Session.from_dict(session_data)
                        # Only load active sessions
                        if session.status == 'active':
                            self.sessions[session.session_id] = session
                            self.ip_to_session[session.ip_address] = session.session_id
                self.logger.info(f"Loaded {len(self.sessions)} active sessions")
            except Exception as e:
                self.logger.error(f"Failed to load sessions: {e}")
    
    def save_sessions(self):
        """Save sessions to file"""
        try:
            data = {
                'sessions': [s.to_dict() for s in self.sessions.values()],
                'updated_at': datetime.now().isoformat()
            }
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save sessions: {e}")
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        import hashlib
        timestamp = str(time.time())
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]
    
    def get_available_ports(self) -> Optional[tuple]:
        """Get available port set (vnc_display, vnc_port, novnc_port, agent_port)"""
        used_displays = {s.vnc_display for s in self.sessions.values() if s.status == 'active'}
        
        for i in range(MAX_CONCURRENT_SESSIONS):
            display = VNC_DISPLAY_START + i
            if display not in used_displays:
                vnc_port = 5900 + display
                novnc_port = NOVNC_PORT_START + i
                agent_port = AGENT_PORT_START + i
                return (display, vnc_port, novnc_port, agent_port)
        
        return None
    
    def get_session_by_ip(self, ip_address: str) -> Optional[Session]:
        """Get existing session for IP, verify it's still running"""
        session_id = self.ip_to_session.get(ip_address)
        if session_id:
            session = self.sessions.get(session_id)
            if session and session.status == 'active':
                # Verify VNC is still running
                result = subprocess.run(
                    ['pgrep', '-f', f'Xtigervnc :{session.vnc_display}'],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    return session
                else:
                    # Services died, clean up this session
                    self.logger.warning(f"Session {session_id} services not running, cleaning up")
                    self.close_session(session_id)
        return None
    
    def create_session(self, ip_address: str, vnc_file: str = "vnc.html", url: str = None, 
                        screen_width: int = 375, screen_height: int = 812, user_agent: str = '') -> Optional[Session]:
        """Create a new session for IP"""
        with self.lock:
            # Check if session already exists
            existing = self.get_session_by_ip(ip_address)
            if existing:
                self.logger.info(f"Returning existing session for {ip_address}")
                self.update_activity(existing.session_id)
                return existing
            
            # Check concurrent limit
            active_count = sum(1 for s in self.sessions.values() if s.status == 'active')
            if active_count >= MAX_CONCURRENT_SESSIONS:
                self.logger.warning(f"Max concurrent sessions reached ({MAX_CONCURRENT_SESSIONS})")
                return None
            
            # Get available ports
            ports = self.get_available_ports()
            if not ports:
                self.logger.error("No available ports")
                return None
            
            vnc_display, vnc_port, novnc_port, agent_port = ports
            
            # Create session
            session_id = self.generate_session_id()
            chrome_profile = f"profile_{session_id}"
            now = datetime.now().isoformat()
            
            session = Session(
                session_id=session_id,
                ip_address=ip_address,
                vnc_display=vnc_display,
                vnc_port=vnc_port,
                novnc_port=novnc_port,
                agent_port=agent_port,
                chrome_profile=chrome_profile,
                vnc_file=vnc_file,
                created_at=now,
                last_activity=now,
                status='active',
                screen_width=screen_width,
                screen_height=screen_height,
                user_agent=user_agent
            )
            
            # Start session services
            if self.start_session_services(session, url):
                self.sessions[session_id] = session
                self.ip_to_session[ip_address] = session_id
                self.save_sessions()
                self.logger.info(f"Created session {session_id} for {ip_address} on display :{vnc_display} ({screen_width}x{screen_height})")
                return session
            else:
                self.logger.error(f"Failed to start services for session {session_id}")
                return None
    
    def start_session_services(self, session: Session, url: str = None) -> bool:
        """Start VNC, Chrome, Agent, and Websockify for session"""
        try:
            # 1. Kill existing VNC on this display first
            subprocess.run(['vncserver', '-kill', f':{session.vnc_display}'], 
                         capture_output=True)
            time.sleep(0.5)
            
            # Use session's screen dimensions
            width = session.screen_width
            height = session.screen_height
            
            # Start VNC server with device's screen size and high quality
            vnc_cmd = [
                'vncserver',
                f':{session.vnc_display}',
                '-geometry', f'{width}x{height}',
                '-depth', '32',
                '-localhost', 'no'
            ]
            
            self.logger.info(f"Starting VNC: {' '.join(vnc_cmd)}")
            
            vnc_result = subprocess.run(
                vnc_cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if vnc_result.returncode != 0:
                self.logger.error(f"VNC failed: {vnc_result.stderr}")
                return False
            
            time.sleep(1)
            
            # Verify VNC is running
            result = subprocess.run(
                ['pgrep', '-f', f'Xtigervnc :{session.vnc_display}'],
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                self.logger.error("VNC server not running after start")
                return False
            
            session.pid_vnc = int(result.stdout.strip().split()[0])
            self.logger.info(f"VNC started on display :{session.vnc_display} (PID: {session.pid_vnc})")
            
            # 2. Start Websockify for this session
            websockify_cmd = [
                'websockify',
                '--web=/usr/share/novnc',
                f'0.0.0.0:{session.novnc_port}',
                f'localhost:{session.vnc_port}'
            ]
            
            self.logger.info(f"Starting Websockify: {' '.join(websockify_cmd)}")
            
            websockify_process = subprocess.Popen(
                websockify_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            session.pid_websockify = websockify_process.pid
            time.sleep(0.5)
            
            self.logger.info(f"Websockify started on port {session.novnc_port} (PID: {session.pid_websockify})")
            
            # 3. Start Chrome with profile and matching screen size
            chrome_profile_dir = CHROME_PROFILES_DIR / session.chrome_profile
            chrome_profile_dir.mkdir(parents=True, exist_ok=True)
            
            env = os.environ.copy()
            env['DISPLAY'] = f':{session.vnc_display}'
            env['ACCESSIBILITY_ENABLED'] = '1'
            env['GTK_MODULES'] = 'gail:atk-bridge'
            
            # Detect if mobile user agent
            user_agent = session.user_agent
            is_mobile = any(x in user_agent.lower() for x in ['iphone', 'android', 'mobile'])
            
            chrome_cmd = [
                'google-chrome',
                f'--user-data-dir={chrome_profile_dir}',
                '--disable-gpu',
                '--no-sandbox',
                '--force-renderer-accessibility',
                '--disable-infobars',
                '--disable-session-crashed-bubble',
                '--no-first-run',
                '--kiosk',
                f'--window-size={width},{height}',
                '--force-device-scale-factor=0.75',  # 75% zoom
            ]
            
            # Add mobile user agent if connecting from mobile
            if is_mobile:
                chrome_cmd.append(f'--user-agent={user_agent}')
            
            if url:
                chrome_cmd.append(url)
            
            self.logger.info(f"Starting Chrome on display :{session.vnc_display} ({width}x{height})")
            
            chrome_process = subprocess.Popen(
                chrome_cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            session.pid_chrome = chrome_process.pid
            time.sleep(1)
            
            self.logger.info(f"Chrome started (PID: {session.pid_chrome})")
            
            # 4. Start Keyboard Agent for this session
            agent_script = Path(__file__).parent / 'agent.py'
            
            agent_env = env.copy()
            agent_cmd = [
                'python3',
                str(agent_script),
                '--port', str(session.agent_port),
                '--display', f':{session.vnc_display}'
            ]
            
            self.logger.info(f"Starting Agent on port {session.agent_port}")
            
            agent_process = subprocess.Popen(
                agent_cmd,
                env=agent_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            session.pid_agent = agent_process.pid
            
            self.logger.info(f"Agent started (PID: {session.pid_agent})")
            self.logger.info(f"Session {session.session_id} fully started")
            
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("VNC server start timed out")
            self.stop_session_services(session)
            return False
        except Exception as e:
            self.logger.error(f"Failed to start session services: {e}")
            self.stop_session_services(session)
            return False
    
    def stop_session_services(self, session: Session):
        """Stop all services for a session"""
        try:
            # Kill Chrome
            if session.pid_chrome:
                try:
                    os.kill(session.pid_chrome, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            
            # Kill Agent
            if session.pid_agent:
                try:
                    os.kill(session.pid_agent, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            
            # Kill Websockify
            if session.pid_websockify:
                try:
                    os.kill(session.pid_websockify, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            
            # Kill VNC
            subprocess.run(
                ['vncserver', '-kill', f':{session.vnc_display}'],
                capture_output=True
            )
            
            self.logger.info(f"Stopped services for session {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
    
    def update_activity(self, session_id: str):
        """Update last activity timestamp"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].last_activity = datetime.now().isoformat()
                self.save_sessions()
    
    def close_session(self, session_id: str):
        """Close a session"""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                self.stop_session_services(session)
                session.status = 'closed'
                
                # Remove from IP mapping
                if session.ip_address in self.ip_to_session:
                    del self.ip_to_session[session.ip_address]
                
                # Remove from active sessions
                del self.sessions[session_id]
                
                self.save_sessions()
                self.logger.info(f"Closed session {session_id}")
    
    def check_timeouts(self):
        """Check for timed out sessions"""
        now = datetime.now()
        timeout_delta = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        
        with self.lock:
            expired = []
            for session_id, session in self.sessions.items():
                if session.status == 'active':
                    last_activity = datetime.fromisoformat(session.last_activity)
                    if now - last_activity > timeout_delta:
                        expired.append(session_id)
            
            for session_id in expired:
                self.logger.info(f"Session {session_id} timed out")
                self.close_session(session_id)
    
    def cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            time.sleep(60)  # Check every minute
            self.check_timeouts()
    
    def start(self):
        """Start the session manager"""
        self.running = True
        self.cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.logger.info("Session manager started")
    
    def stop(self):
        """Stop the session manager"""
        self.running = False
        
        # Close all active sessions
        with self.lock:
            for session_id in list(self.sessions.keys()):
                self.close_session(session_id)
        
        self.logger.info("Session manager stopped")
    
    def get_all_sessions(self) -> List[Session]:
        """Get all active sessions"""
        return list(self.sessions.values())
    
    def get_stats(self) -> dict:
        """Get session statistics"""
        active = sum(1 for s in self.sessions.values() if s.status == 'active')
        return {
            'active_sessions': active,
            'max_sessions': MAX_CONCURRENT_SESSIONS,
            'available_slots': MAX_CONCURRENT_SESSIONS - active,
            'timeout_minutes': SESSION_TIMEOUT_MINUTES,
            'port_range': f"{NOVNC_PORT_START}-{NOVNC_PORT_END}",
            'admin_port': ADMIN_PORT
        }


# ============================================
# SINGLETON INSTANCE
# ============================================

_manager_instance = None

def get_session_manager() -> SessionManager:
    """Get singleton session manager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SessionManager()
    return _manager_instance


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    manager = get_session_manager()
    manager.start()
    
    print("Session Manager Test")
    print("=" * 50)
    print(f"Stats: {manager.get_stats()}")
    
    # Test creating a session
    print("\nCreating test session...")
    session = manager.create_session("127.0.0.1", "vnc.html", "https://google.com")
    
    if session:
        print(f"Session created: {session.session_id}")
        print(f"  VNC Display: :{session.vnc_display}")
        print(f"  noVNC Port: {session.novnc_port}")
        print(f"  Agent Port: {session.agent_port}")
        print(f"  Chrome Profile: {session.chrome_profile}")
        
        input("\nPress Enter to close session...")
        manager.close_session(session.session_id)
    else:
        print("Failed to create session")
    
    manager.stop()
