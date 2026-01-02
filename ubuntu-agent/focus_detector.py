#!/usr/bin/env python3
"""
Focus Detector for noVNC Keyboard Agent
Detects when a text input field is focused in Chrome/Chromium
Uses AT-SPI2 accessibility API
"""

import subprocess
import os
import yaml
from pathlib import Path

# Try to import accessibility libraries
try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
    ATSPI_AVAILABLE = True
except (ImportError, ValueError):
    ATSPI_AVAILABLE = False


class FocusDetector:
    def __init__(self, config_path=None):
        """Initialize the focus detector"""
        self.config = self._load_config(config_path)
        self.enabled_apps = self._get_enabled_apps()
        
        # Initialize AT-SPI if available
        if ATSPI_AVAILABLE:
            try:
                Atspi.init()
                self.use_atspi = True
            except Exception:
                self.use_atspi = False
        else:
            self.use_atspi = False
    
    def _load_config(self, config_path):
        """Load configuration from yaml file"""
        if config_path is None:
            config_path = Path.home() / ".config" / "novnc-keyboard" / "config.yaml"
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default config if file not found
            return self._default_config()
    
    def _default_config(self):
        """Return default configuration"""
        return {
            'detection': {
                'poll_interval': 100,
                'method': 'accessibility',
                'auto_detect': True
            },
            'apps': {
                'chrome': {
                    'enabled': True,
                    'process_names': [
                        'google-chrome',
                        'google-chrome-stable',
                        'google-chrome-beta',
                        'chrome'
                    ],
                    'window_classes': [
                        'Google-chrome',
                        'Google-chrome-stable'
                    ]
                },
                'chromium': {
                    'enabled': True,
                    'process_names': ['chromium-browser', 'chromium'],
                    'window_classes': ['Chromium-browser', 'Chromium']
                }
            }
        }
    
    def _get_enabled_apps(self):
        """Get list of enabled apps from config"""
        enabled = {
            'process_names': [],
            'window_classes': []
        }
        
        apps = self.config.get('apps', {})
        for app_name, app_config in apps.items():
            if app_config.get('enabled', False):
                enabled['process_names'].extend(app_config.get('process_names', []))
                enabled['window_classes'].extend(app_config.get('window_classes', []))
        
        return enabled
    
    def get_active_window_info(self):
        """Get active window ID and class using xdotool and xprop"""
        try:
            # Get active window ID
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode != 0:
                return None, None
            
            window_id = result.stdout.strip()
            
            # Get window class
            result = subprocess.run(
                ['xprop', '-id', window_id, 'WM_CLASS'],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode != 0:
                return window_id, None
            
            # Parse WM_CLASS output: WM_CLASS(STRING) = "instance", "class"
            output = result.stdout.strip()
            if 'WM_CLASS' in output and '=' in output:
                parts = output.split('=')[1].strip()
                # Extract class name (second value)
                classes = [c.strip().strip('"') for c in parts.split(',')]
                window_class = classes[-1] if classes else None
                return window_id, window_class
            
            return window_id, None
            
        except subprocess.TimeoutExpired:
            return None, None
        except Exception:
            return None, None
    
    def is_enabled_app_active(self):
        """Check if an enabled app window is currently active"""
        window_id, window_class = self.get_active_window_info()
        
        if window_class is None:
            return False
        
        # Check against enabled window classes
        for enabled_class in self.enabled_apps['window_classes']:
            if enabled_class.lower() in window_class.lower():
                return True
        
        # Auto-detect fallback
        if self.config.get('detection', {}).get('auto_detect', True):
            # Check for common browser patterns
            browser_patterns = ['chrome', 'chromium', 'firefox', 'browser']
            for pattern in browser_patterns:
                if pattern in window_class.lower():
                    return True
        
        return False
    
    def is_text_field_focused(self):
        """
        Check if a text input field is currently focused.
        Uses AT-SPI accessibility API if available, otherwise falls back to
        window-based detection.
        """
        # First check if an enabled app is active
        if not self.is_enabled_app_active():
            return False
        
        # If AT-SPI is available, use it for precise detection
        if self.use_atspi:
            return self._check_atspi_focus()
        
        # Fallback: assume text field is focused if enabled app is active
        # (less accurate but works without accessibility API)
        return True
    
    def _check_atspi_focus(self):
        """Use AT-SPI to check if focused element is a text input"""
        try:
            # Get the focused object
            desktop = Atspi.get_desktop(0)
            
            if desktop is None:
                return self.is_enabled_app_active()
            
            # Iterate through applications
            for i in range(desktop.get_child_count()):
                app = desktop.get_child_at_index(i)
                if app is None:
                    continue
                
                # Check if this app is one of our enabled apps
                app_name = app.get_name()
                if not self._is_enabled_app_name(app_name):
                    continue
                
                # Find focused element in this app
                focused = self._find_focused_element(app)
                if focused and self._is_text_input(focused):
                    return True
            
            return False
            
        except Exception:
            # Fallback to window-based detection on error
            return self.is_enabled_app_active()
    
    def _is_enabled_app_name(self, app_name):
        """Check if app name matches enabled apps"""
        if app_name is None:
            return False
        
        app_name_lower = app_name.lower()
        
        for process_name in self.enabled_apps['process_names']:
            if process_name.lower() in app_name_lower:
                return True
        
        # Auto-detect
        if self.config.get('detection', {}).get('auto_detect', True):
            browser_patterns = ['chrome', 'chromium']
            for pattern in browser_patterns:
                if pattern in app_name_lower:
                    return True
        
        return False
    
    def _find_focused_element(self, accessible, depth=0, max_depth=20):
        """Recursively find the focused element in an accessible tree"""
        if depth > max_depth:
            return None
        
        try:
            # Check if this element has focus
            state_set = accessible.get_state_set()
            if state_set and state_set.contains(Atspi.StateType.FOCUSED):
                return accessible
            
            # Check children
            child_count = accessible.get_child_count()
            for i in range(child_count):
                child = accessible.get_child_at_index(i)
                if child:
                    result = self._find_focused_element(child, depth + 1, max_depth)
                    if result:
                        return result
            
            return None
            
        except Exception:
            return None
    
    def _is_text_input(self, accessible):
        """Check if an accessible element is a text input field"""
        try:
            role = accessible.get_role()
            
            # Text input roles
            text_roles = [
                Atspi.Role.ENTRY,
                Atspi.Role.TEXT,
                Atspi.Role.PARAGRAPH,
                Atspi.Role.TERMINAL,
                Atspi.Role.PASSWORD_TEXT,
                Atspi.Role.EDITBAR,
                Atspi.Role.DOCUMENT_TEXT,
                Atspi.Role.DOCUMENT_FRAME,
                Atspi.Role.DOCUMENT_WEB,
            ]
            
            if role in text_roles:
                return True
            
            # Check if element is editable
            state_set = accessible.get_state_set()
            if state_set:
                if state_set.contains(Atspi.StateType.EDITABLE):
                    return True
            
            # Check interfaces
            interfaces = accessible.get_interfaces()
            if 'EditableText' in interfaces:
                return True
            
            return False
            
        except Exception:
            return False
    
    def get_focus_state(self):
        """
        Get detailed focus state information.
        Returns dict with focus info for debugging/logging.
        """
        window_id, window_class = self.get_active_window_info()
        is_enabled_app = self.is_enabled_app_active()
        is_text_focused = self.is_text_field_focused()
        
        return {
            'window_id': window_id,
            'window_class': window_class,
            'is_enabled_app': is_enabled_app,
            'is_text_focused': is_text_focused,
            'atspi_available': self.use_atspi
        }


def check_dependencies():
    """Check and report missing dependencies"""
    missing = []
    
    # Check xdotool
    try:
        subprocess.run(['which', 'xdotool'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        missing.append('xdotool')
    
    # Check xprop
    try:
        subprocess.run(['which', 'xprop'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        missing.append('x11-utils (xprop)')
    
    # Check AT-SPI
    if not ATSPI_AVAILABLE:
        missing.append('gir1.2-atspi-2.0 (python3-gi)')
    
    return missing


def install_dependencies():
    """Install missing dependencies"""
    print("Installing dependencies...")
    
    packages = [
        'xdotool',
        'x11-utils',
        'python3-gi',
        'gir1.2-atspi-2.0',
        'at-spi2-core',
        'python3-yaml'
    ]
    
    try:
        subprocess.run(
            ['sudo', 'apt', 'install', '-y'] + packages,
            check=True
        )
        print("[!] Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[X] Failed to install dependencies: {e}")
        return False


# Test function
if __name__ == "__main__":
    import time
    
    print("=" * 50)
    print("  Focus Detector Test")
    print("=" * 50)
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"\n[*]  Missing dependencies: {', '.join(missing)}")
        response = input("Install them now? (y/n): ")
        if response.lower() == 'y':
            install_dependencies()
        else:
            print("Some features may not work without dependencies.")
    
    print("\nInitializing focus detector...")
    detector = FocusDetector()
    
    print(f"AT-SPI available: {detector.use_atspi}")
    print(f"Enabled apps: {detector.enabled_apps}")
    print("\nMonitoring focus (press Ctrl+C to stop)...\n")
    
    try:
        last_state = None
        while True:
            state = detector.get_focus_state()
            
            # Only print when state changes
            if state != last_state:
                print(f"Window: {state['window_class']} | "
                      f"Enabled App: {state['is_enabled_app']} | "
                      f"Text Focused: {state['is_text_focused']}")
                last_state = state
            
            time.sleep(0.1)  # 100ms poll interval
            
    except KeyboardInterrupt:
        print("\n\nStopped.")
