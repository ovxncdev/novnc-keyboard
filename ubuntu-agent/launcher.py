#!/usr/bin/env python3
"""
noVNC Keyboard - Interactive Setup & Launcher
"""

import os
import sys
import subprocess
import json
import time
import signal
from pathlib import Path

# ============================================
# CONFIGURATION
# ============================================

CONFIG_DIR = Path.home() / ".config" / "novnc-keyboard"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
URLS_FILE = CONFIG_DIR / "saved_urls.json"
NOVNC_DIR = Path("/usr/share/novnc")
SCRIPT_DIR = Path(__file__).parent.resolve()

# Colors
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    DIM = '\033[2m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

C = Colors()

# ============================================
# UTILITIES
# ============================================

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_banner():
    banner = f"""
{C.CYAN}{C.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              ⌨️  noVNC Keyboard System                        ║
║                                                               ║
║          Mobile keyboard overlay for noVNC                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{C.RESET}"""
    print(banner)

def print_menu(title, options, show_back=True):
    """Print a styled menu"""
    print(f"\n{C.CYAN}{C.BOLD}  {title}{C.RESET}\n")
    print(f"  {C.DIM}{'─' * 45}{C.RESET}\n")
    
    for key, label in options:
        if key == '0':
            print(f"  {C.DIM}{'─' * 45}{C.RESET}")
        print(f"  {C.CYAN}[{C.WHITE}{C.BOLD}{key}{C.RESET}{C.CYAN}]{C.RESET}  {label}")
    
    print()

def get_input(prompt, default=None):
    """Get user input with optional default"""
    if default:
        result = input(f"  {C.CYAN}>{C.RESET} {prompt} [{C.DIM}{default}{C.RESET}]: ").strip()
        return result if result else default
    return input(f"  {C.CYAN}>{C.RESET} {prompt}: ").strip()

def get_choice(prompt="Select option"):
    """Get menu choice"""
    return input(f"  {C.CYAN}▸{C.RESET} {prompt}: ").strip()

def print_success(msg):
    print(f"\n  {C.GREEN}✓{C.RESET} {msg}")

def print_error(msg):
    print(f"\n  {C.RED}✗{C.RESET} {msg}")

def print_info(msg):
    print(f"\n  {C.CYAN}ℹ{C.RESET} {msg}")

def print_warning(msg):
    print(f"\n  {C.YELLOW}⚠{C.RESET} {msg}")

def pause():
    input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

# ============================================
# URL MANAGEMENT
# ============================================

def load_urls():
    """Load saved URLs"""
    if URLS_FILE.exists():
        with open(URLS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_urls(urls):
    """Save URLs to file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(URLS_FILE, 'w') as f:
        json.dump(urls, f, indent=2)

def add_url():
    """Add a new URL"""
    clear()
    print_banner()
    print(f"\n{C.CYAN}{C.BOLD}  Add New URL{C.RESET}\n")
    
    name = get_input("Name (e.g., Facebook)")
    url = get_input("URL (e.g., https://facebook.com)")
    
    if not url.startswith('http'):
        url = 'https://' + url
    
    urls = load_urls()
    urls.append({'name': name, 'url': url})
    save_urls(urls)
    
    print_success(f"Added: {name} → {url}")
    pause()

def remove_url():
    """Remove a saved URL"""
    urls = load_urls()
    if not urls:
        print_warning("No saved URLs")
        pause()
        return
    
    clear()
    print_banner()
    print(f"\n{C.CYAN}{C.BOLD}  Remove URL{C.RESET}\n")
    
    for i, item in enumerate(urls, 1):
        print(f"  {C.CYAN}[{i}]{C.RESET} {item['name']} - {C.DIM}{item['url']}{C.RESET}")
    print(f"  {C.CYAN}[0]{C.RESET} Cancel")
    
    choice = get_choice("Select URL to remove")
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(urls):
            removed = urls.pop(idx)
            save_urls(urls)
            print_success(f"Removed: {removed['name']}")
        elif choice == '0':
            return
    except ValueError:
        print_error("Invalid selection")
    
    pause()

def manage_urls():
    """URL management menu"""
    while True:
        clear()
        print_banner()
        
        urls = load_urls()
        
        print(f"\n{C.CYAN}{C.BOLD}  Saved URLs ({len(urls)}){C.RESET}\n")
        
        if urls:
            for i, item in enumerate(urls, 1):
                print(f"  {C.DIM}{i}.{C.RESET} {item['name']} - {C.DIM}{item['url']}{C.RESET}")
        else:
            print(f"  {C.DIM}No saved URLs{C.RESET}")
        
        print_menu("Options", [
            ('1', 'Add URL'),
            ('2', 'Remove URL'),
            ('0', 'Back')
        ])
        
        choice = get_choice()
        
        if choice == '1':
            add_url()
        elif choice == '2':
            remove_url()
        elif choice == '0':
            break

# ============================================
# SETTINGS
# ============================================

def load_config():
    """Load YAML config"""
    try:
        import yaml
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return yaml.safe_load(f)
    except ImportError:
        pass
    return get_default_config()

def save_config(config):
    """Save YAML config"""
    try:
        import yaml
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except ImportError:
        pass

def get_default_config():
    return {
        'server': {
            'host': '0.0.0.0',
            'port': 6082
        },
        'detection': {
            'poll_interval': 100,
            'method': 'accessibility',
            'auto_detect': True
        },
        'apps': {
            'chrome': {
                'enabled': True,
                'process_names': ['google-chrome', 'google-chrome-stable', 'chromium-browser'],
                'window_classes': ['Google-chrome', 'Chromium-browser']
            }
        },
        'keyboard': {
            'layout': 'qwerty_us',
            'position': 'bottom',
            'sound': True,
            'key_preview': True,
            'theme': 'auto'
        },
        'logging': {
            'level': 'info',
            'file': str(CONFIG_DIR / 'agent.log')
        }
    }

def settings_menu():
    """Settings menu"""
    while True:
        clear()
        print_banner()
        
        config = load_config()
        
        print_menu("Settings", [
            ('1', f"WebSocket Port: {C.WHITE}{config['server']['port']}{C.RESET}"),
            ('2', f"Poll Interval: {C.WHITE}{config['detection']['poll_interval']}ms{C.RESET}"),
            ('3', f"Log Level: {C.WHITE}{config['logging']['level']}{C.RESET}"),
            ('4', f"Keyboard Sound: {C.WHITE}{'On' if config['keyboard']['sound'] else 'Off'}{C.RESET}"),
            ('5', f"Key Preview: {C.WHITE}{'On' if config['keyboard']['key_preview'] else 'Off'}{C.RESET}"),
            ('6', f"Theme: {C.WHITE}{config['keyboard']['theme']}{C.RESET}"),
            ('0', 'Back')
        ])
        
        choice = get_choice()
        
        if choice == '1':
            port = get_input("WebSocket Port", str(config['server']['port']))
            config['server']['port'] = int(port)
            save_config(config)
            print_success("Port updated")
            pause()
        elif choice == '2':
            interval = get_input("Poll Interval (ms)", str(config['detection']['poll_interval']))
            config['detection']['poll_interval'] = int(interval)
            save_config(config)
            print_success("Poll interval updated")
            pause()
        elif choice == '3':
            print(f"\n  {C.DIM}Options: debug, info, warning, error{C.RESET}")
            level = get_input("Log Level", config['logging']['level'])
            config['logging']['level'] = level
            save_config(config)
            print_success("Log level updated")
            pause()
        elif choice == '4':
            config['keyboard']['sound'] = not config['keyboard']['sound']
            save_config(config)
            print_success(f"Sound {'enabled' if config['keyboard']['sound'] else 'disabled'}")
            pause()
        elif choice == '5':
            config['keyboard']['key_preview'] = not config['keyboard']['key_preview']
            save_config(config)
            print_success(f"Key preview {'enabled' if config['keyboard']['key_preview'] else 'disabled'}")
            pause()
        elif choice == '6':
            print(f"\n  {C.DIM}Options: auto, light, dark{C.RESET}")
            theme = get_input("Theme", config['keyboard']['theme'])
            config['keyboard']['theme'] = theme
            save_config(config)
            print_success("Theme updated")
            pause()
        elif choice == '0':
            break

# ============================================
# CHROME LAUNCHER
# ============================================

def start_chrome(url=None, kiosk=True):
    """Start Chrome with accessibility enabled"""
    env = os.environ.copy()
    env['DISPLAY'] = ':1.0'
    env['ACCESSIBILITY_ENABLED'] = '1'
    env['GTK_MODULES'] = 'gail:atk-bridge'
    
    cmd = [
        'google-chrome',
        '--disable-gpu',
        '--no-sandbox',
        '--force-renderer-accessibility',
        '--disable-infobars',
        '--disable-session-crashed-bubble',
        '--no-first-run'
    ]
    
    if kiosk:
        cmd.append('--kiosk')
    
    if url:
        cmd.append(url)
    
    try:
        # Kill existing Chrome
        subprocess.run(['pkill', '-f', 'google-chrome'], capture_output=True)
        time.sleep(1)
        
        # Start new Chrome
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return process
    except Exception as e:
        print_error(f"Failed to start Chrome: {e}")
        return None

# ============================================
# AGENT LAUNCHER
# ============================================

def start_agent():
    """Start the keyboard agent"""
    env = os.environ.copy()
    env['DISPLAY'] = ':1.0'
    
    agent_path = SCRIPT_DIR / 'agent.py'
    
    try:
        process = subprocess.Popen(
            ['python3', str(agent_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        return process
    except Exception as e:
        print_error(f"Failed to start agent: {e}")
        return None

def check_agent_running():
    """Check if agent is already running"""
    result = subprocess.run(
        ['pgrep', '-f', 'agent.py'],
        capture_output=True
    )
    return result.returncode == 0

def stop_agent():
    """Stop the keyboard agent"""
    subprocess.run(['pkill', '-f', 'agent.py'], capture_output=True)

# ============================================
# INSTALLATION
# ============================================

def check_dependencies():
    """Check and install dependencies"""
    deps = {
        'python3-gi': 'python3-gi',
        'gir1.2-atspi-2.0': 'gir1.2-atspi-2.0',
        'at-spi2-core': 'at-spi2-core',
        'xdotool': 'xdotool',
        'x11-utils': 'x11-utils',
        'python3-yaml': 'python3-yaml',
        'python3-websockets': 'python3-websockets'
    }
    
    missing = []
    
    for pkg in deps.values():
        result = subprocess.run(
            ['dpkg', '-s', pkg],
            capture_output=True
        )
        if result.returncode != 0:
            missing.append(pkg)
    
    return missing

def install_dependencies(missing):
    """Install missing dependencies"""
    if not missing:
        return True
    
    print_info(f"Installing: {', '.join(missing)}")
    
    result = subprocess.run(
        ['sudo', 'apt', 'install', '-y'] + missing,
        capture_output=True
    )
    
    return result.returncode == 0

def install_keyboard_html():
    """Copy keyboard.html to noVNC directory"""
    src = SCRIPT_DIR.parent / 'keyboard-overlay' / 'keyboard.html'
    dst = NOVNC_DIR / 'keyboard.html'
    
    if not src.exists():
        # Try alternate location
        src = SCRIPT_DIR / 'keyboard.html'
    
    if src.exists():
        try:
            subprocess.run(['sudo', 'cp', str(src), str(dst)], check=True)
            return True
        except:
            return False
    return False

def setup_config():
    """Setup initial configuration"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    if not CONFIG_FILE.exists():
        save_config(get_default_config())
    
    if not URLS_FILE.exists():
        save_urls([
            {'name': 'Google', 'url': 'https://google.com'},
            {'name': 'Facebook', 'url': 'https://facebook.com'}
        ])

def create_systemd_service():
    """Create systemd service file"""
    service_content = f"""[Unit]
Description=noVNC Keyboard Multi-User Server
After=network.target

[Service]
Type=simple
User={os.environ.get('USER', 'ubuntu')}
WorkingDirectory={SCRIPT_DIR}
ExecStart=/usr/bin/python3 {SCRIPT_DIR}/start_server.py --url "https://gmail.com" --vnc "vnc_lite.html"
Restart=always
RestartSec=5
Environment=HOME=/home/{os.environ.get('USER', 'ubuntu')}

[Install]
WantedBy=multi-user.target
"""
    
    service_path = '/etc/systemd/system/novnc-keyboard.service'
    
    try:
        # Write service file
        with open('/tmp/novnc-keyboard.service', 'w') as f:
            f.write(service_content)
        
        subprocess.run(['sudo', 'cp', '/tmp/novnc-keyboard.service', service_path], check=True)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        return True
    except:
        return False

def run_installation():
    """Run full installation"""
    clear()
    print_banner()
    print(f"\n{C.CYAN}{C.BOLD}  Installation{C.RESET}\n")
    
    steps = [
        ("Checking dependencies", check_dependencies),
        ("Setting up config", setup_config),
        ("Installing keyboard overlay", install_keyboard_html),
        ("Creating systemd service", create_systemd_service)
    ]
    
    # Check dependencies
    print(f"  {C.DIM}[1/4]{C.RESET} Checking dependencies...")
    missing = check_dependencies()
    if missing:
        print(f"  {C.YELLOW}→{C.RESET} Missing: {', '.join(missing)}")
        if not install_dependencies(missing):
            print_error("Failed to install dependencies")
            pause()
            return
    print(f"  {C.GREEN}✓{C.RESET} Dependencies OK")
    
    # Setup config
    print(f"  {C.DIM}[2/4]{C.RESET} Setting up config...")
    setup_config()
    print(f"  {C.GREEN}✓{C.RESET} Config created")
    
    # Install keyboard HTML
    print(f"  {C.DIM}[3/4]{C.RESET} Installing keyboard overlay...")
    if install_keyboard_html():
        print(f"  {C.GREEN}✓{C.RESET} Keyboard overlay installed")
    else:
        print(f"  {C.YELLOW}⚠{C.RESET} Keyboard overlay not found (copy manually)")
    
    # Create systemd service
    print(f"  {C.DIM}[4/4]{C.RESET} Creating systemd service...")
    if create_systemd_service():
        print(f"  {C.GREEN}✓{C.RESET} Systemd service created")
    else:
        print(f"  {C.YELLOW}⚠{C.RESET} Systemd service failed (run agent manually)")
    
    print_success("Installation complete!")
    pause()

# ============================================
# CLEANUP FUNCTION
# ============================================

def kill_all_services():
    """Kill all running services"""
    subprocess.run(['sudo', 'fuser', '-k', '6080/tcp'], capture_output=True)
    subprocess.run(['sudo', 'fuser', '-k', '6081/tcp'], capture_output=True)
    subprocess.run(['sudo', 'fuser', '-k', '6082/tcp'], capture_output=True)
    subprocess.run(['pkill', '-f', 'websockify'], capture_output=True)
    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3.*agent'], capture_output=True)
    subprocess.run(['pkill', 'unclutter'], capture_output=True)
    for i in range(1, 11):
        subprocess.run(['vncserver', '-kill', f':{i}'], capture_output=True)
    
    # Clear sessions
    sessions_file = CONFIG_DIR / 'sessions.json'
    if sessions_file.exists():
        sessions_file.unlink()

# ============================================
# MAIN MENU
# ============================================

def start_menu():
    """Chrome start options"""
    while True:
        clear()
        print_banner()
        
        urls = load_urls()
        
        # First, choose VNC file
        print_menu("Select VNC Interface", [
            ('1', 'vnc.html (Full featured)'),
            ('2', 'vnc_lite.html (Lightweight - Recommended)'),
            ('0', 'Back')
        ])
        
        vnc_choice = get_choice("Select VNC interface")
        
        if vnc_choice == '0':
            return (None, None, None)
        elif vnc_choice == '1':
            vnc_file = 'vnc.html'
        elif vnc_choice == '2':
            vnc_file = 'vnc_lite.html'
        else:
            vnc_file = 'vnc_lite.html'
        
        clear()
        print_banner()
        
        options = [
            ('1', 'Enter custom URL'),
            ('2', 'Start with blank page'),
            ('3', f"Start Chrome only (no kiosk)"),
            ('4', f"Agent only (no Chrome)"),
            ('5', f"{C.MAGENTA}Multi-user mode (start server){C.RESET}"),
        ]
        
        # Add saved URLs
        if urls:
            options.append(('', f'{C.DIM}── Saved URLs ──{C.RESET}'))
            for i, item in enumerate(urls):
                options.append((str(i + 6), f"{item['name']} {C.DIM}({item['url']}){C.RESET}"))
        
        options.append(('0', 'Back'))
        
        print_menu("Start Options", options)
        
        choice = get_choice()
        
        if choice == '1':
            url = get_input("Enter URL")
            if not url.startswith('http'):
                url = 'https://' + url
            return ('kiosk', url, vnc_file)
        elif choice == '2':
            return ('kiosk', None, vnc_file)
        elif choice == '3':
            url = get_input("Enter URL (or leave empty)", "")
            return ('normal', url if url else None, vnc_file)
        elif choice == '4':
            return ('agent_only', None, vnc_file)
        elif choice == '5':
            # Multi-user mode - ask for URL
            clear()
            print_banner()
            print(f"\n{C.CYAN}{C.BOLD}  Multi-User Mode - Set Target URL{C.RESET}\n")
            
            urls = load_urls()
            
            print(f"  {C.CYAN}[1]{C.RESET} Enter custom URL")
            print(f"  {C.CYAN}[2]{C.RESET} Blank page (no URL)")
            
            if urls:
                print(f"\n  {C.DIM}── Saved URLs ──{C.RESET}")
                for i, item in enumerate(urls):
                    print(f"  {C.CYAN}[{i + 3}]{C.RESET} {item['name']} {C.DIM}({item['url']}){C.RESET}")
            
            print(f"\n  {C.CYAN}[0]{C.RESET} Back")
            
            url_choice = get_choice()
            
            if url_choice == '0':
                continue
            elif url_choice == '1':
                url = get_input("Enter URL")
                if url and not url.startswith('http'):
                    url = 'https://' + url
                return ('multi_user', url, vnc_file)
            elif url_choice == '2':
                return ('multi_user', '', vnc_file)
            else:
                try:
                    idx = int(url_choice) - 3
                    if 0 <= idx < len(urls):
                        return ('multi_user', urls[idx]['url'], vnc_file)
                except ValueError:
                    pass
        elif choice == '0':
            continue
        else:
            try:
                idx = int(choice) - 6
                if 0 <= idx < len(urls):
                    return ('kiosk', urls[idx]['url'], vnc_file)
            except ValueError:
                pass

def run_system(mode, url, vnc_file='vnc_lite.html'):
    """Run Chrome and Agent"""
    clear()
    print_banner()
    
    # Multi-user mode
    if mode == 'multi_user':
        run_multi_user_server(vnc_file, url)
        return
    
    chrome_process = None
    agent_process = None
    
    print(f"\n{C.CYAN}{C.BOLD}  Starting System{C.RESET}\n")
    print(f"  {C.DIM}VNC Interface: {vnc_file}{C.RESET}\n")
    
    # Start Chrome
    if mode != 'agent_only':
        kiosk = (mode == 'kiosk')
        print(f"  {C.DIM}Starting Chrome...{C.RESET}")
        chrome_process = start_chrome(url, kiosk)
        if chrome_process:
            print(f"  {C.GREEN}✓{C.RESET} Chrome started" + (f" → {url}" if url else ""))
        else:
            print(f"  {C.RED}✗{C.RESET} Chrome failed to start")
        time.sleep(2)
    
    # Start Agent
    print(f"  {C.DIM}Starting Agent...{C.RESET}")
    agent_process = start_agent()
    
    if agent_process:
        print(f"  {C.GREEN}✓{C.RESET} Agent started on port 6082")
    else:
        print(f"  {C.RED}✗{C.RESET} Agent failed to start")
        pause()
        return
    
    config = load_config()
    port = config['server']['port']
    
    print(f"""
{C.CYAN}{'─' * 55}{C.RESET}

  {C.GREEN}System Running!{C.RESET}
  
  {C.DIM}Access keyboard at:{C.RESET}
  {C.WHITE}http://<your-ip>:6081/keyboard.html{C.RESET}
  
  {C.DIM}Agent WebSocket:{C.RESET}
  {C.WHITE}ws://<your-ip>:{port}{C.RESET}

{C.CYAN}{'─' * 55}{C.RESET}

  {C.YELLOW}Press Ctrl+C to stop{C.RESET}
""")
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n\n  {C.YELLOW}Stopping...{C.RESET}")
        if agent_process:
            agent_process.terminate()
        if chrome_process:
            chrome_process.terminate()
        print(f"  {C.GREEN}✓{C.RESET} Stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Stream agent output
    try:
        while True:
            if agent_process.poll() is not None:
                print_error("Agent stopped unexpectedly")
                break
            
            line = agent_process.stdout.readline()
            if line:
                # Color the output
                if 'ERROR' in line:
                    print(f"  {C.RED}{line.strip()}{C.RESET}")
                elif 'WARNING' in line:
                    print(f"  {C.YELLOW}{line.strip()}{C.RESET}")
                elif 'INFO' in line:
                    print(f"  {C.DIM}{line.strip()}{C.RESET}")
                else:
                    print(f"  {line.strip()}")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        signal_handler(None, None)


def run_multi_user_server(default_vnc_file='vnc_lite.html', url=''):
    """Run multi-user session server"""
    clear()
    print_banner()
    
    print(f"\n{C.CYAN}{C.BOLD}  Starting Multi-User Server{C.RESET}\n")
    
    # Clean up first
    print(f"  {C.DIM}Cleaning up old processes...{C.RESET}")
    kill_all_services()
    time.sleep(1)
    print(f"  {C.GREEN}✓{C.RESET} Cleanup done")
    
    # Import session manager and admin panel
    try:
        from session_manager import get_session_manager
        from admin_panel import AdminServer, ADMIN_PORT, set_server_config
    except ImportError as e:
        print_error(f"Failed to import session manager: {e}")
        pause()
        return
    
    # Set server config (URL and VNC file)
    set_server_config(url=url, vnc_file=default_vnc_file)
    print(f"  {C.DIM}URL: {url if url else '(none)'}{C.RESET}")
    print(f"  {C.DIM}VNC: {default_vnc_file}{C.RESET}\n")
    
    # Start session manager
    print(f"  {C.DIM}Starting session manager...{C.RESET}")
    manager = get_session_manager()
    manager.start()
    print(f"  {C.GREEN}✓{C.RESET} Session manager started")
    
    # Start admin panel
    print(f"  {C.DIM}Starting admin panel...{C.RESET}")
    admin_server = AdminServer()
    admin_server.start()
    print(f"  {C.GREEN}✓{C.RESET} Admin panel started on port {ADMIN_PORT}")
    
    stats = manager.get_stats()
    
    print(f"""
{C.CYAN}{'─' * 55}{C.RESET}

  {C.GREEN}Multi-User Server Running!{C.RESET}
  
  {C.DIM}Admin Panel:{C.RESET}
  {C.WHITE}http://<your-ip>:{ADMIN_PORT}/admin{C.RESET}
  
  {C.DIM}User Connect URL:{C.RESET}
  {C.WHITE}http://<your-ip>:{ADMIN_PORT}/connect{C.RESET}
  
  {C.DIM}Target URL:{C.RESET} {C.WHITE}{url if url else '(blank page)'}{C.RESET}
  {C.DIM}Max concurrent users:{C.RESET} {C.WHITE}{stats['max_sessions']}{C.RESET}
  {C.DIM}Session timeout:{C.RESET} {C.WHITE}{stats['timeout_minutes']} minutes{C.RESET}
  {C.DIM}Port range:{C.RESET} {C.WHITE}{stats['port_range']}{C.RESET}

{C.CYAN}{'─' * 55}{C.RESET}

  {C.YELLOW}Press Ctrl+C to stop{C.RESET}
""")
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n\n  {C.YELLOW}Stopping...{C.RESET}")
        admin_server.stop()
        manager.stop()
        print(f"  {C.GREEN}✓{C.RESET} Stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

def status_menu():
    """Show system status"""
    clear()
    print_banner()
    
    print(f"\n{C.CYAN}{C.BOLD}  System Status{C.RESET}\n")
    
    # Check agent
    agent_running = check_agent_running()
    print(f"  Agent:    {C.GREEN}● Running{C.RESET}" if agent_running else f"  Agent:    {C.RED}○ Stopped{C.RESET}")
    
    # Check Chrome
    chrome_result = subprocess.run(['pgrep', '-f', 'google-chrome'], capture_output=True)
    chrome_running = chrome_result.returncode == 0
    print(f"  Chrome:   {C.GREEN}● Running{C.RESET}" if chrome_running else f"  Chrome:   {C.RED}○ Stopped{C.RESET}")
    
    # Check systemd service
    service_result = subprocess.run(
        ['systemctl', 'is-active', 'novnc-keyboard'],
        capture_output=True,
        text=True
    )
    service_active = service_result.stdout.strip() == 'active'
    print(f"  Service:  {C.GREEN}● Active{C.RESET}" if service_active else f"  Service:  {C.DIM}○ Inactive{C.RESET}")
    
    # Check sessions
    sessions_file = CONFIG_DIR / 'sessions.json'
    session_count = 0
    if sessions_file.exists():
        try:
            with open(sessions_file) as f:
                data = json.load(f)
                session_count = len([s for s in data.get('sessions', []) if s.get('status') == 'active'])
        except:
            pass
    print(f"  Sessions: {C.WHITE}{session_count}{C.RESET}")
    
    # Config info
    config = load_config()
    print(f"\n  {C.DIM}Port: {config['server']['port']}{C.RESET}")
    print(f"  {C.DIM}Config: {CONFIG_FILE}{C.RESET}")
    
    # Port status
    print(f"\n  {C.DIM}Port Status:{C.RESET}")
    for port in [6080, 6081, 6082, 6101, 6102]:
        result = subprocess.run(['sudo', 'fuser', f'{port}/tcp'], capture_output=True, text=True)
        status = f"{C.GREEN}●{C.RESET}" if result.stdout.strip() else f"{C.DIM}○{C.RESET}"
        print(f"    {port}: {status}")
    
    pause()

def main_menu():
    """Main menu"""
    while True:
        clear()
        print_banner()
        
        print_menu("Main Menu", [
            ('1', f'{C.GREEN}▶ Start System{C.RESET}'),
            ('2', 'System Status'),
            ('3', 'Manage URLs'),
            ('4', 'Settings'),
            ('5', 'Run Installation'),
            ('6', f'{C.RED}Stop All Services{C.RESET}'),
            ('0', 'Exit')
        ])
        
        choice = get_choice()
        
        if choice == '1':
            result = start_menu()
            if result[0]:
                mode, url, vnc_file = result
                run_system(mode, url, vnc_file)
        elif choice == '2':
            status_menu()
        elif choice == '3':
            manage_urls()
        elif choice == '4':
            settings_menu()
        elif choice == '5':
            run_installation()
        elif choice == '6':
            clear()
            print_banner()
            print(f"\n{C.YELLOW}Stopping all services...{C.RESET}\n")
            kill_all_services()
            print_success("All services stopped")
            pause()
        elif choice == '0':
            clear()
            print(f"\n  {C.CYAN}Goodbye!{C.RESET}\n")
            break

# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    # Check if running with arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--install':
            run_installation()
        elif sys.argv[1] == '--start':
            url = sys.argv[2] if len(sys.argv) > 2 else None
            run_system('kiosk', url)
        elif sys.argv[1] == '--agent':
            run_system('agent_only', None)
        elif sys.argv[1] == '--multi':
            url = sys.argv[2] if len(sys.argv) > 2 else ''
            run_multi_user_server('vnc_lite.html', url)
        elif sys.argv[1] == '--stop':
            kill_all_services()
            print("All services stopped")
        elif sys.argv[1] == '--help':
            print(f"""
{C.CYAN}noVNC Keyboard System{C.RESET}

Usage: {sys.argv[0]} [option]

Options:
  --install       Run installation
  --start [url]   Start system with optional URL
  --agent         Start agent only (no Chrome)
  --multi [url]   Start multi-user server
  --stop          Stop all services
  --help          Show this help

Without options, starts interactive menu.
""")
        else:
            print_error(f"Unknown option: {sys.argv[1]}")
    else:
        main_menu()
