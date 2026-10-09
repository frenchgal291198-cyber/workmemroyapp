"""Read the active window and idle time on macOS, Windows and Linux (X11).

Uses only built-in OS tools, no extra installs, except on Linux where
`xdotool` (and optionally `xprintidle`) are needed.
"""

import os
import platform
import re
import shutil
import subprocess
from typing import Optional, Tuple

SYSTEM = platform.system()

_MAC_SCRIPT = '''
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    set winTitle to ""
    try
        set winTitle to name of front window of frontApp
    end try
end tell
return appName & linefeed & winTitle
'''


def _run(cmd, timeout=5) -> Optional[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


# --- macOS ------------------------------------------------------------------

def _mac_window():
    out = _run(["osascript", "-e", _MAC_SCRIPT])
    if out is None:
        return None
    app, _, title = out.rstrip("\n").partition("\n")
    return app.strip(), title.strip()


def _mac_idle():
    out = _run(["ioreg", "-c", "IOHIDSystem"])
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out or "")
    return int(m.group(1)) / 1e9 if m else None


# --- Windows ----------------------------------------------------------------

def _win_window():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app = ""
    handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if handle:
        size = wintypes.DWORD(1024)
        pbuf = ctypes.create_unicode_buffer(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, pbuf, ctypes.byref(size)):
            app = os.path.splitext(os.path.basename(pbuf.value))[0]
        kernel32.CloseHandle(handle)
    return app, buf.value


def _win_idle():
    import ctypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    millis = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return millis / 1000.0


# --- Linux (X11) ------------------------------------------------------------

def _linux_window():
    if not shutil.which("xdotool"):
        return None
    title = _run(["xdotool", "getactivewindow", "getwindowname"])
    if title is None:
        return None
    app = ""
    pid = _run(["xdotool", "getactivewindow", "getwindowpid"])
    if pid and pid.strip().isdigit():
        try:
            with open(f"/proc/{pid.strip()}/comm") as f:
                app = f.read().strip()
        except OSError:
            pass
    return app, title.strip()


def _linux_idle():
    if not shutil.which("xprintidle"):
        return None
    out = _run(["xprintidle"])
    return int(out.strip()) / 1000.0 if out and out.strip().isdigit() else None


def active_window() -> Optional[Tuple[str, str]]:
    """(app name, window title) of whatever you're looking at, or None if unknown."""
    try:
        if SYSTEM == "Darwin":
            return _mac_window()
        if SYSTEM == "Windows":
            return _win_window()
        if SYSTEM == "Linux":
            return _linux_window()
    except Exception:
        return None
    return None


def idle_seconds() -> Optional[float]:
    """Seconds since the last keyboard/mouse input, or None if this OS can't tell us."""
    try:
        if SYSTEM == "Darwin":
            return _mac_idle()
        if SYSTEM == "Windows":
            return _win_idle()
        if SYSTEM == "Linux":
            return _linux_idle()
    except Exception:
        return None
    return None


def notify(title: str, message: str):
    """Best-effort desktop notification."""
    try:
        if SYSTEM == "Darwin":
            esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
            _run(["osascript", "-e", f'display notification "{esc(message)}" with title "{esc(title)}"'])
        elif SYSTEM == "Linux" and shutil.which("notify-send"):
            _run(["notify-send", title, message])
        elif SYSTEM == "Windows":
            ps = ("[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null;"
                  "$n = New-Object System.Windows.Forms.NotifyIcon;"
                  "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true;"
                  "$n.ShowBalloonTip(8000, $env:BB_TITLE, $env:BB_MSG, 'Info'); Start-Sleep 9; $n.Dispose()")
            env = dict(os.environ, BB_TITLE=title, BB_MSG=message)
            subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                             env=env, creationflags=0x08000000)  # CREATE_NO_WINDOW
    except Exception:
        pass
