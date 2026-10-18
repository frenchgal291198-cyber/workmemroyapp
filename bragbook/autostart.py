"""Start the tracker automatically when you log in, so you never have to remember to."""

import os
import platform
import subprocess
import sys
from pathlib import Path

LABEL = "com.bragbook.tracker"
# The folder that contains the bragbook package, so the background job can find it
# even when it was installed by install.sh rather than pip.
PKG_PARENT = str(Path(__file__).resolve().parent.parent)


def _mac_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _linux_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart" / "bragbook.desktop"


def _win_path() -> Path:
    return (Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu"
            / "Programs" / "Startup" / "bragbook.vbs")


def install() -> str:
    system = platform.system()
    py = sys.executable
    if system == "Darwin":
        from bragbook import config
        log = config.home() / "tracker.log"
        path = _mac_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{py}</string><string>-m</string><string>bragbook</string><string>track</string></array>
  <key>EnvironmentVariables</key><dict><key>PYTHONPATH</key><string>{PKG_PARENT}</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>
""")
        subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
        subprocess.run(["launchctl", "load", "-w", str(path)], capture_output=True)
        return (f"Installed {path}. The tracker is running now and will start at every login.\n"
                "Your dashboard: http://localhost:8642 (bookmark it!)\n"
                "If macOS asks, allow your Terminal / Python under System Settings → Privacy & Security → "
                "Accessibility, so Brag Book can read window titles.")
    if system == "Windows":
        pyw = Path(py).with_name("pythonw.exe")
        exe = str(pyw if pyw.exists() else py)
        path = _win_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'CreateObject("Wscript.Shell").Run """{exe}"" -m bragbook track", 0, False\n')
        subprocess.Popen([exe, "-m", "bragbook", "track"], creationflags=0x08000000)
        return (f"Installed {path}. The tracker is running now and will start at every login.\n"
                "Your dashboard: http://localhost:8642 (bookmark it!)")
    if system == "Linux":
        path = _linux_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"[Desktop Entry]\nType=Application\nName=Brag Book tracker\n"
                        f"Exec=env PYTHONPATH={PKG_PARENT} {py} -m bragbook track\nX-GNOME-Autostart-enabled=true\nNoDisplay=true\n")
        return f"Installed {path}. Brag Book will start at your next login (run `bragbook track` to start now)."
    return f"Autostart isn't supported on {system}. Run `bragbook track` instead."


def remove() -> str:
    system = platform.system()
    path = {"Darwin": _mac_path, "Windows": _win_path, "Linux": _linux_path}.get(system, lambda: None)()
    if path is None or not path.exists():
        return "Autostart wasn't installed."
    if system == "Darwin":
        subprocess.run(["launchctl", "unload", "-w", str(path)], capture_output=True)
    path.unlink()
    return f"Removed {path}. (On Windows/Linux, a tracker that's already running keeps going until you log out.)"
