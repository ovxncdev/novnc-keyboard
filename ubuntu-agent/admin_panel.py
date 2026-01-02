#!/usr/bin/env python3
"""
noVNC Keyboard - Admin Panel & Session Router
Web interface for managing sessions and routing users
"""

import os
import json
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket

from session_manager import get_session_manager, ADMIN_PORT, NOVNC_PORT_START

# ============================================
# HTML TEMPLATES
# ============================================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>noVNC Keyboard - Admin Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .header p {
            color: rgba(255,255,255,0.6);
            font-size: 14px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .stat-card h3 {
            font-size: 12px;
            color: rgba(255,255,255,0.5);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .stat-card .value {
            font-size: 36px;
            font-weight: 700;
            color: #0a84ff;
        }

        .stat-card .value.warning {
            color: #ff9f0a;
        }

        .stat-card .value.success {
            color: #30d158;
        }

        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .section h2 {
            font-size: 18px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        th {
            font-size: 12px;
            color: rgba(255,255,255,0.5);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        td {
            font-size: 14px;
        }

        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }

        .status.active {
            background: rgba(48, 209, 88, 0.2);
            color: #30d158;
        }

        .status.inactive {
            background: rgba(255, 159, 10, 0.2);
            color: #ff9f0a;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn-danger {
            background: rgba(255, 69, 58, 0.2);
            color: #ff453a;
        }

        .btn-danger:hover {
            background: rgba(255, 69, 58, 0.4);
        }

        .btn-primary {
            background: rgba(10, 132, 255, 0.2);
            color: #0a84ff;
        }

        .btn-primary:hover {
            background: rgba(10, 132, 255, 0.4);
        }

        .refresh-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            color: rgba(255,255,255,0.6);
        }

        .auto-refresh input {
            width: 18px;
            height: 18px;
        }

        .no-sessions {
            text-align: center;
            padding: 40px;
            color: rgba(255,255,255,0.4);
        }

        .ip-address {
            font-family: monospace;
            background: rgba(255,255,255,0.1);
            padding: 2px 8px;
            border-radius: 4px;
        }

        .port {
            color: #0a84ff;
            font-family: monospace;
        }

        .time-ago {
            color: rgba(255,255,255,0.5);
            font-size: 12px;
        }

        @media (max-width: 768px) {
            .stats {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .section {
                padding: 15px;
                overflow-x: auto;
            }
            
            table {
                font-size: 12px;
                min-width: 600px;
            }
            
            th, td {
                padding: 8px 6px;
                white-space: nowrap;
            }
            
            .header h1 {
                font-size: 22px;
            }
            
            .refresh-bar {
                flex-direction: column;
                gap: 15px;
                align-items: flex-start;
            }
            
            .btn {
                width: 100%;
                text-align: center;
            }
        }
        
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            
            .stats {
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            
            .stat-card {
                padding: 15px;
            }
            
            .stat-card .value {
                font-size: 28px;
            }
            
            .header {
                padding: 20px 0;
            }
            
            .header h1 {
                font-size: 18px;
            }
            
            .section h2 {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⌨️ noVNC Keyboard Admin</h1>
            <p>Multi-user session management</p>
        </div>

        <div class="stats" id="stats">
            <!-- Stats loaded via JS -->
        </div>

        <div class="refresh-bar">
            <div class="auto-refresh">
                <input type="checkbox" id="autoRefresh" checked>
                <label for="autoRefresh">Auto-refresh every 5s</label>
            </div>
            <button class="btn btn-primary" onclick="loadData()">↻ Refresh Now</button>
        </div>

        <div class="section">
            <h2>Active Sessions</h2>
            <div id="sessions">
                <!-- Sessions loaded via JS -->
            </div>
        </div>
    </div>

    <script>
        let autoRefreshInterval;

        function timeAgo(dateStr) {
            const date = new Date(dateStr);
            const now = new Date();
            const seconds = Math.floor((now - date) / 1000);
            
            if (seconds < 60) return `${seconds}s ago`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
            return `${Math.floor(seconds / 86400)}d ago`;
        }

        function renderStats(stats) {
            document.getElementById('stats').innerHTML = `
                <div class="stat-card">
                    <h3>Active Sessions</h3>
                    <div class="value ${stats.active_sessions >= stats.max_sessions ? 'warning' : 'success'}">${stats.active_sessions}</div>
                </div>
                <div class="stat-card">
                    <h3>Max Sessions</h3>
                    <div class="value">${stats.max_sessions}</div>
                </div>
                <div class="stat-card">
                    <h3>Available Slots</h3>
                    <div class="value success">${stats.available_slots}</div>
                </div>
                <div class="stat-card">
                    <h3>Session Timeout</h3>
                    <div class="value">${stats.timeout_minutes}m</div>
                </div>
            `;
        }

        function renderSessions(sessions) {
            if (sessions.length === 0) {
                document.getElementById('sessions').innerHTML = `
                    <div class="no-sessions">No active sessions</div>
                `;
                return;
            }

            let html = `
                <table>
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>Display</th>
                            <th>noVNC Port</th>
                            <th>Agent Port</th>
                            <th>Profile</th>
                            <th>Last Activity</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            sessions.forEach(session => {
                html += `
                    <tr>
                        <td><span class="ip-address">${session.ip_address}</span></td>
                        <td>:${session.vnc_display}</td>
                        <td><span class="port">${session.novnc_port}</span></td>
                        <td><span class="port">${session.agent_port}</span></td>
                        <td>${session.chrome_profile}</td>
                        <td><span class="time-ago">${timeAgo(session.last_activity)}</span></td>
                        <td><span class="status ${session.status}">${session.status}</span></td>
                        <td>
                            <button class="btn btn-danger" onclick="closeSession('${session.session_id}')">Close</button>
                        </td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            document.getElementById('sessions').innerHTML = html;
        }

        async function loadData() {
            try {
                const response = await fetch('/api/sessions');
                const data = await response.json();
                renderStats(data.stats);
                renderSessions(data.sessions);
            } catch (error) {
                console.error('Failed to load data:', error);
            }
        }

        async function closeSession(sessionId) {
            if (!confirm('Close this session?')) return;
            
            try {
                await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
                loadData();
            } catch (error) {
                console.error('Failed to close session:', error);
            }
        }

        function toggleAutoRefresh() {
            const enabled = document.getElementById('autoRefresh').checked;
            if (enabled) {
                autoRefreshInterval = setInterval(loadData, 5000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }

        document.getElementById('autoRefresh').addEventListener('change', toggleAutoRefresh);
        
        // Initial load
        loadData();
        toggleAutoRefresh();
    </script>
</body>
</html>
"""

ROUTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Connecting...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .loader {
            text-align: center;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #0a84ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }

        p {
            color: rgba(255,255,255,0.6);
            font-size: 14px;
        }

        .error {
            color: #ff453a;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="loader">
        <div class="spinner"></div>
        <h1>Setting up your session...</h1>
        <p>Please wait while we prepare your workspace</p>
        <p id="error" class="error" style="display:none;"></p>
    </div>

    <script>
        async function connect() {
            const params = new URLSearchParams(window.location.search);
            const vnc_file = params.get('vnc') || 'vnc.html';
            const url = params.get('url') || '';
            
            try {
                const response = await fetch('/api/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ vnc_file, url })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Redirect to the session's keyboard page
                    window.location.href = data.redirect_url;
                } else {
                    document.getElementById('error').textContent = data.error || 'Failed to create session';
                    document.getElementById('error').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('error').textContent = 'Connection failed: ' + error.message;
                document.getElementById('error').style.display = 'block';
            }
        }
        
        connect();
    </script>
</body>
</html>
"""

KEYBOARD_WRAPPER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>noVNC Session</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; background: #000; }
        #vnc-iframe { width: 100%; height: 100%; border: none; }
    </style>
</head>
<body>
    <iframe id="vnc-iframe" src="SESSION_VNC_URL"></iframe>
    <script>
        // Activity tracking
        const SESSION_ID = 'SESSION_ID_PLACEHOLDER';
        const AGENT_PORT = AGENT_PORT_PLACEHOLDER;
        
        // Send activity ping every 30 seconds
        setInterval(() => {
            fetch('/api/activity/' + SESSION_ID, { method: 'POST' });
        }, 30000);
        
        // Load keyboard overlay script
        const script = document.createElement('script');
        script.src = '/keyboard.js?port=' + AGENT_PORT;
        document.body.appendChild(script);
    </script>
</body>
</html>
"""


# ============================================
# REQUEST HANDLER
# ============================================

class AdminHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def get_client_ip(self):
        # Check for forwarded IP
        forwarded = self.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return self.client_address[0]
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        manager = get_session_manager()
        
        if path == '/' or path == '/admin':
            self.send_html(ADMIN_HTML)
        
        elif path == '/connect':
            self.send_html(ROUTER_HTML)
        
        elif path == '/api/sessions':
            sessions = manager.get_all_sessions()
            stats = manager.get_stats()
            self.send_json({
                'sessions': [s.to_dict() for s in sessions],
                'stats': stats
            })
        
        elif path.startswith('/session/'):
            # Serve session-specific keyboard page
            session_id = path.split('/')[2]
            if session_id in manager.sessions:
                session = manager.sessions[session_id]
                # Generate keyboard page for this session
                html = KEYBOARD_WRAPPER_HTML
                vnc_url = f"http://{self.headers.get('Host').split(':')[0]}:{session.novnc_port}/{session.vnc_file}"
                html = html.replace('SESSION_VNC_URL', vnc_url)
                html = html.replace('SESSION_ID_PLACEHOLDER', session_id)
                html = html.replace('AGENT_PORT_PLACEHOLDER', str(session.agent_port))
                self.send_html(html)
            else:
                self.send_json({'error': 'Session not found'}, 404)
        
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        manager = get_session_manager()
        client_ip = self.get_client_ip()
        
        if path == '/api/connect':
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
            
            try:
                data = json.loads(body)
            except:
                data = {}
            
            vnc_file = data.get('vnc_file', 'vnc.html')
            url = data.get('url', '')
            
            # Create or get session
            session = manager.create_session(client_ip, vnc_file, url)
            
            if session:
                host = self.headers.get('Host', 'localhost').split(':')[0]
                redirect_url = f"http://{host}:{ADMIN_PORT}/session/{session.session_id}"
                self.send_json({
                    'success': True,
                    'session_id': session.session_id,
                    'redirect_url': redirect_url,
                    'novnc_port': session.novnc_port,
                    'agent_port': session.agent_port
                })
            else:
                self.send_json({
                    'success': False,
                    'error': 'Failed to create session. Maximum sessions reached.'
                }, 503)
        
        elif path.startswith('/api/activity/'):
            session_id = path.split('/')[3]
            manager.update_activity(session_id)
            self.send_json({'success': True})
        
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        manager = get_session_manager()
        
        if path.startswith('/api/sessions/'):
            session_id = path.split('/')[3]
            manager.close_session(session_id)
            self.send_json({'success': True})
        else:
            self.send_json({'error': 'Not found'}, 404)


# ============================================
# SERVER
# ============================================

class AdminServer:
    def __init__(self, port=ADMIN_PORT):
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        self.server = HTTPServer(('0.0.0.0', self.port), AdminHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Admin panel running at http://0.0.0.0:{self.port}/admin")
        print(f"User connect URL: http://0.0.0.0:{self.port}/connect")
    
    def stop(self):
        if self.server:
            self.server.shutdown()


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    manager = get_session_manager()
    manager.start()
    
    server = AdminServer()
    server.start()
    
    print("\nAdmin server running. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()
        manager.stop()
