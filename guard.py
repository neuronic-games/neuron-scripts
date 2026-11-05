# guard.py v3.1
# Neuronic 2025
# Cross-platform: Windows kiosk features active on Windows only.

import os, sys

_IS_WIN = sys.platform == 'win32'
_IS_MAC = sys.platform == 'darwin'

# ── Logging: set up first so import errors are captured ──────────────────────
if __name__ == '__main__':
    _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guard.log')
    _log_file = open(_log_path, 'w', buffering=1)
    class _Tee:
        def __init__(self, *streams): self.streams = streams
        def write(self, data):
            for s in self.streams:
                try:
                    s.write(data)
                except UnicodeEncodeError:
                    s.write(data.encode('ascii', errors='replace').decode('ascii'))
        def flush(self):
            for s in self.streams: s.flush()
    sys.stdout = _Tee(sys.__stdout__, _log_file)
    sys.stderr = _Tee(sys.__stderr__, _log_file)
    print('guard.py starting...')
    print('Press Ctrl+Shift+S to quit and restore desktop.')

import time, subprocess, logging
from datetime import datetime
from threading import Thread, Event

import settings_loader  # must run before `import settings` below
import settings
import archive_update

# ── Windows-only imports ──────────────────────────────────────────────────────
if _IS_WIN:
    import ctypes
    from ctypes import byref, c_int, windll
    from ctypes.wintypes import RGB

# ── Settings ──────────────────────────────────────────────────────────────────
APP_EXE_PATH  = getattr(settings, 'appEXEPath',        '')
APP_EXE_NAME  = getattr(settings, 'appEXEName',        '')
# Command-line arguments passed to APP_EXE_NAME when guard.py launches it
# (not used for the Chrome-kiosk case, which has its own hardcoded flags).
# Expected as a list (e.g. ["-fullscreen", "-vrmode"]) since an app can
# need more than one; a bare string is also accepted and treated as a
# single argument, in case someone sets it that way by mistake.
_app_exe_param_raw = getattr(settings, 'appEXEParam', [])
APP_EXE_PARAMS = [_app_exe_param_raw] if isinstance(_app_exe_param_raw, str) else list(_app_exe_param_raw)
crash_path    = getattr(settings, 'crashPath',         'crash.log')
logo_brand    = getattr(settings, 'logoBrand',         'neuronic.png')

desktop_color = getattr(settings, 'desktopColor',      RGB(0, 0, 0)) if _IS_WIN else None
reset_desktop = getattr(settings, 'resetDesktopColor', RGB(0, 0, 0)) if _IS_WIN else None

# Background color for the no-app lock window (see show_lock_window()) - a
# Tk color string, e.g. "#403a7a" or a name like "black".
lock_screen_color = getattr(settings, 'lockScreenColor', '#403a7a')

# Keep a start screen (restartMessage) up on every display while the app
# runs (Windows only), at the bottom of the window stack: it only hides
# the desktop, so while the app is crashed/restarting you see the message
# instead. The app, OBS and any other window stay in front of it.
lock_behind_app = bool(getattr(settings, 'lockBehindApp', True))

# Optional text shown under the start screen's animation (start_screen.py),
# and its color. Blank = animation only.
restart_message       = getattr(settings, 'restartMessage', '')
restart_message_color = getattr(settings, 'restartMessageColor', 'white')

# If no app is configured at all, guard.py just locks the desktop behind
# the logo (see initApp()) with nothing to launch/monitor - not an error
# case, just a valid "nothing installed on this deployment yet" state.
NO_APP_CONFIGURED = not APP_EXE_NAME

_script_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(_script_dir, crash_path),
    filemode='w', level=logging.INFO,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def kill_app():
    if not APP_EXE_NAME:
        return
    if _IS_WIN:
        os.system(f'taskkill /im "{APP_EXE_NAME}" /f >nul 2>&1')
    else:
        subprocess.run(['pkill', '-f', APP_EXE_NAME], capture_output=True)

def kill_pulse():
    # pulse.py runs as its own separate `python pulse.py` process (started
    # alongside guard.py by launch.cmd), so it isn't touched by kill_app().
    # Match on command line rather than taskkill /im python.exe so we don't
    # also kill guard.py's own process (or any other unrelated python.exe).
    if _IS_WIN:
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like '*pulse.py*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        )
        os.system(f'powershell -NoProfile -Command "{ps_cmd}" >nul 2>&1')
    else:
        subprocess.run(['pkill', '-f', 'pulse.py'], capture_output=True)

def _wait_for_keypress():
    if _IS_WIN:
        try:
            import msvcrt
            msvcrt.getch()
            return
        except Exception:
            pass
    try:
        input()
    except Exception:
        pass

def check_app_exists():
    """Verify the app configured via appEXEPath/appEXEName is actually
    there before we hide the desktop and start monitoring it. Chrome kiosk
    mode is exempt - it launches a URL, not a local EXE. If appEXEName is
    blank, no app is configured at all - that's not an error, it just
    means initApp()/startAllProcess() lock the desktop behind the logo
    with nothing to monitor (see NO_APP_CONFIGURED)."""
    if NO_APP_CONFIGURED:
        return True

    is_chrome = 'Chrome' in APP_EXE_PATH or 'chrome' in APP_EXE_PATH
    if is_chrome:
        return True

    path = os.path.join(APP_EXE_PATH, APP_EXE_NAME)
    if os.path.isfile(path):
        return True

    print('=' * 70)
    print('ERROR: Application not found:')
    print(f'  {path}')
    print('Check appEXEPath and appEXEName in settings.py.')
    print('=' * 70)
    print('Press any key to exit...')
    _wait_for_keypress()

    # pulse.py is started separately (before guard.py, per launch.cmd) and
    # would otherwise keep monitoring/reporting for an app that never runs.
    kill_pulse()
    return False

def _pids_named(exe_name):
    """PIDs of every running process whose image name is exe_name. Uses a
    process snapshot, which (unlike OpenProcess) also works when the app
    runs elevated / as administrator."""
    from ctypes import wintypes
    kernel32 = windll.kernel32

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)]

    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    target = exe_name.lower()
    pids = set()
    snap = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        return pids
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, byref(entry))
        while ok:
            if entry.szExeFile.lower() == target:
                pids.add(entry.th32ProcessID)
            ok = kernel32.Process32NextW(snap, byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return pids


def _find_app_windows(exe_name):
    """Visible, non-empty, non-topmost top-level windows of the app's
    process(es), front to back (EnumWindows order). Owned windows count
    too: many frameworks (Delphi, AIR, some .NET apps) make the visible
    main window owned by a hidden one. [] if none are up yet. Pure ctypes -
    cheap enough to call every second from the Tk loop."""
    from ctypes import wintypes
    user32 = windll.user32
    user32.GetWindowLongW.argtypes = [wintypes.HWND, c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    pids = _pids_named(exe_name)
    found = []
    if not pids:
        return found

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        if pid.value not in pids:
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x8:  # WS_EX_TOPMOST: above us anyway
            return True
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, byref(r))
        if r.right - r.left > 0 and r.bottom - r.top > 0:
            found.append(hwnd)
        return True

    user32.EnumWindows(_cb, 0)
    return found


def _window_title(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    windll.user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def _make_dpi_aware():
    """Work in real pixels on every monitor, so the windows line up with
    each display exactly even when displays use different scaling (125%,
    150%...). Must run before any window is created."""
    try:
        windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _monitor_rects():
    """[(x, y, width, height, is_primary), ...] for every display, primary
    first. Falls back to just the primary screen if enumeration fails."""
    from ctypes import wintypes
    user32 = windll.user32

    class MONITORINFO(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]

    rects = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                         ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def _cb(hmon, _hdc, _rect, _):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, byref(info)):
            r = info.rcMonitor
            rects.append((r.left, r.top, r.right - r.left, r.bottom - r.top,
                          bool(info.dwFlags & 1)))  # MONITORINFOF_PRIMARY
        return True

    try:
        user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
    except Exception as e:
        print(f'Could not list displays ({e}) - covering the main one only.')
    if not rects:
        rects = [(0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1), True)]
    rects.sort(key=lambda r: not r[4])
    return rects


def _lowest_window_above_desktop(exclude):
    """The bottom-most window that's actually on screen above the desktop:
    visible, non-empty, not always-on-top (those stay above us anyway, and
    inserting below one would make our window always-on-top too), and not
    one of ours. Stops at the desktop itself (Progman / WorkerW). 0 if
    there are no such windows."""
    from ctypes import wintypes
    user32 = windll.user32
    user32.GetWindowLongW.argtypes = [wintypes.HWND, c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, c_int]
    lowest = [0]
    cls = ctypes.create_unicode_buffer(64)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _):
        if hwnd in exclude or not user32.IsWindowVisible(hwnd):
            return True
        user32.GetClassNameW(hwnd, cls, 64)
        if cls.value in ('Progman', 'WorkerW'):
            return False  # reached the desktop - everything below is behind it
        if user32.GetWindowLongW(hwnd, -20) & 0x8:  # WS_EX_TOPMOST
            return True
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, byref(r))
        if r.right - r.left > 0 and r.bottom - r.top > 0:
            lowest[0] = hwnd
        return True

    user32.EnumWindows(_cb, 0)
    return lowest[0]


def show_lock_window(quit_event, behind_app=False, on_ready=None):
    """Borderless windows (lock_screen_color background), one covering each
    display, blocking access to the desktop underneath (the wallpaper /
    desktop-color trick set in initApp() alone doesn't stop someone from
    reaching desktop icons in every case - an actual covering window does).

    behind_app=False (no app configured): the windows are always on top,
    with the logo centered on the main display.

    behind_app=True: the windows show restart_message and are kept at the
    *bottom* of the window stack, just above the desktop, so they only
    hide the desktop: the app, OBS (main window and projectors) and any
    other window stay in front. When the app crashes/hangs and is
    restarted, the message is what's left instead of the desktop. The
    windows can't be activated (clicking/touching them doesn't bring them
    forward), and they're moved back to the bottom every second in case
    anything reordered them. If displays are added, removed or rearranged
    (e.g. a TV switched off), the windows are rebuilt to match.

    on_ready is called once the windows are up (used to start the app
    monitor only then, so the app's first window opens above them).
    Runs its own Tk event loop on the calling thread (must be the main
    thread) until quit_event is set from elsewhere (e.g. the Ctrl+Shift+S
    hotkey, which runs on its own thread - only quit_event.set() is called
    from there, never anything Tk-related, since Tk isn't thread-safe)."""
    import tkinter as tk
    from ctypes import wintypes

    _make_dpi_aware()
    user32 = windll.user32
    user32.GetAncestor.restype = wintypes.HWND       # 64-bit-safe handles
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, c_int,
                                    c_int, c_int, c_int, wintypes.UINT]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, c_int]
    user32.SetWindowLongW.argtypes = [wintypes.HWND, c_int, ctypes.c_long]
    SWP_FLAGS = 0x0001 | 0x0002 | 0x0010  # NOSIZE | NOMOVE | NOACTIVATE

    root = tk.Tk()
    root.withdraw()  # hidden owner of the per-display windows

    image = None
    if not behind_app:
        logo_path = os.path.join(_script_dir, 'logo', logo_brand)
        if os.path.isfile(logo_path):
            try:
                image = tk.PhotoImage(file=logo_path)
            except Exception as e:
                print(f'Could not load logo image {logo_path}: {e}')

    state = {'monitors': [], 'tops': [], 'hwnds': [], 'screens': [],
             'app_hwnd': 0, 'ticks': 0}
    t0 = time.monotonic()
    if behind_app:
        import start_screen

    def _animate():
        # Only animate while the app's window is gone (starting/restarting)
        # - nobody can see the screen otherwise, so don't spend CPU on it.
        if quit_event.is_set():
            return
        if not state['app_hwnd']:
            t = time.monotonic() - t0
            for screen in state['screens']:
                screen.draw(t)
        root.after(int(1000 / start_screen.FPS) if not state['app_hwnd'] else 500, _animate)

    def _build():
        for top in state['tops']:
            top.destroy()
        state['monitors'] = _monitor_rects()
        state['tops'], state['hwnds'], state['screens'] = [], [], []
        for x, y, w, h, primary in state['monitors']:
            top = tk.Toplevel(root)
            top.overrideredirect(True)
            top.configure(bg=lock_screen_color)
            top.geometry(f'{w}x{h}+{x}+{y}')  # '+-1920' = x of -1920 (a '-' alone means from the right)
            if behind_app:
                # Only ever seen while the app is down: the animated start
                # screen (see start_screen.py), with restartMessage under it.
                canvas = tk.Canvas(top, width=w, height=h, bg=lock_screen_color,
                                   highlightthickness=0, bd=0)
                canvas.place(x=0, y=0)
                screen = start_screen.TkStartScreen(canvas, w, h, lock_screen_color,
                                                    restart_message, restart_message_color)
                screen.draw(time.monotonic() - t0)
                state['screens'].append(screen)
            else:
                top.attributes('-topmost', True)
                label = tk.Label(top, bg=lock_screen_color,
                                 image=image if (image and primary) else None)
                label.image = image  # keep a reference - PhotoImage is GC'd otherwise
                label.place(relx=0.5, rely=0.5, anchor='center')
            top.update_idletasks()
            hwnd = user32.GetAncestor(top.winfo_id(), 2)  # GA_ROOT: the real top-level
            if behind_app:
                # WS_EX_NOACTIVATE (clicks don't raise it) | WS_EX_TOOLWINDOW (no Alt+Tab)
                exstyle = user32.GetWindowLongW(hwnd, -20)
                user32.SetWindowLongW(hwnd, -20, exstyle | 0x08000000 | 0x00000080)
            state['tops'].append(top)
            state['hwnds'].append(hwnd)
        print(f'Lock screen covering {len(state["monitors"])} display(s)'
              + (', behind all other windows.' if behind_app else '.'))

    def _send_to_bottom():
        ours = state['hwnds']
        lowest = _lowest_window_above_desktop(set(ours))
        if lowest:
            user32.SetWindowPos(ours[0], lowest, 0, 0, 0, 0, SWP_FLAGS)
            for prev, hwnd in zip(ours, ours[1:]):
                user32.SetWindowPos(hwnd, prev, 0, 0, 0, 0, SWP_FLAGS)

    def _watch_app():
        windows = _find_app_windows(APP_EXE_NAME)
        app_hwnd = windows[0] if windows else 0
        if app_hwnd and app_hwnd != state['app_hwnd']:
            print(f'App window up ("{_window_title(app_hwnd)}").')
            # New app window (first start or a restart): try to give it
            # focus. Windows may refuse - harmless, it's still in front.
            user32.SetForegroundWindow(app_hwnd)
        elif not app_hwnd and state['app_hwnd']:
            print('App window gone - showing the start screen.')
        state['app_hwnd'] = app_hwnd

    def _poll():
        if quit_event.is_set():
            root.destroy()
            return
        state['ticks'] += 1
        try:
            if state['ticks'] % 5 == 0 and _monitor_rects() != state['monitors']:
                print('Displays changed - rebuilding the lock screen.')
                _build()
            if behind_app:
                _send_to_bottom()
                _watch_app()
        except Exception as e:
            print(f'Lock screen update failed: {e}')
        root.after(1000, _poll)

    def _ready():
        if on_ready:
            on_ready()
        _poll()
        if behind_app:
            _animate()

    _build()
    root.after(200, _ready)
    root.mainloop()

# How the logo wallpaper is placed on the desktop. Windows otherwise reuses
# whatever "fit" was last chosen in Settings -> Personalization -> Background,
# and with Tile/Span it's pinned to the top-left, so the logo lands off-center.
# Optional setting: logoWallpaperStyle = "fit" | "center" | "fill" | "stretch".
_WALLPAPER_STYLES = {           # (WallpaperStyle, TileWallpaper) in HKCU\Control Panel\Desktop
    'center':  ('0',  '0'),
    'stretch': ('2',  '0'),
    'fit':     ('6',  '0'),
    'fill':    ('10', '0'),
}
_prev_wallpaper_style = None    # what the PC had before guard.py changed it

def _write_wallpaper_style(values):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Control Panel\Desktop', 0,
                        winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
        prev = []
        for name in ('WallpaperStyle', 'TileWallpaper'):
            try:
                prev.append(winreg.QueryValueEx(key, name)[0])
            except FileNotFoundError:
                prev.append(None)
        for name, value in zip(('WallpaperStyle', 'TileWallpaper'), values):
            if value is not None:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
    return tuple(prev)

def set_logo_wallpaper_style():
    """Set the wallpaper placement for the logo (default: fit = centered,
    whole image visible). Remembers the previous placement for restore."""
    global _prev_wallpaper_style
    key = str(getattr(settings, 'logoWallpaperStyle', 'fit')).strip().lower()
    style = _WALLPAPER_STYLES.get(key, _WALLPAPER_STYLES['fit'])
    try:
        prev = _write_wallpaper_style(style)
        if _prev_wallpaper_style is None:
            _prev_wallpaper_style = prev
    except Exception as e:
        print(f'Could not set wallpaper style ({e}) - using the current Windows setting.')

def restore_wallpaper_style():
    global _prev_wallpaper_style
    if _prev_wallpaper_style is None:
        return
    try:
        _write_wallpaper_style(_prev_wallpaper_style)
    except Exception as e:
        print(f'Could not restore wallpaper style ({e}).')
    _prev_wallpaper_style = None

def getWallpaper():
    bg = os.path.join(_script_dir, 'background')
    files = os.listdir(bg) if os.path.isdir(bg) else []
    return os.path.join(bg, files[0]) if files else ''

def restore_desktop():
    if _IS_WIN:
        ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(reset_desktop)))
        restore_wallpaper_style()  # before setting the wallpaper, so it applies
        wp = getWallpaper()
        if wp:
            ctypes.windll.user32.SystemParametersInfoW(20, 0, wp, 3)
        windll.user32.ShowWindow(initApp.taskBarStatus, 9)

# ── Init ──────────────────────────────────────────────────────────────────────
def initApp():
    initApp.isStarted = False
    kill_app()
    if _IS_WIN:
        initApp.taskBarStatus     = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
        initApp.consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
        windll.user32.ShowWindow(initApp.taskBarStatus, 0)
        windll.user32.ShowWindow(initApp.consoleBarHandler, 0)
        ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(desktop_color)))
        logo_path = os.path.join(_script_dir, 'logo', logo_brand)
        set_logo_wallpaper_style()  # must come before SystemParametersInfoW to take effect
        ctypes.windll.user32.SystemParametersInfoW(20, 0, logo_path, 3)
    if NO_APP_CONFIGURED:
        print('No app configured (appEXEName is blank) - showing logo, desktop locked.')
        print('Press Ctrl+Shift+S to unlock and exit.')
    else:
        print('Checking status periodically...')

# ── App monitor ───────────────────────────────────────────────────────────────
def getTasks(name):
    try:
        if _IS_WIN:
            for line in os.popen('tasklist /v').read().strip().split('\n'):
                if name in line:
                    return line
        else:
            result = subprocess.run(['pgrep', '-f', name], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
    except Exception:
        pass
    return ''

def getTaskProcess(stop_event):
    import traceback
    try:
        while not stop_event.is_set():
            res = getTasks(APP_EXE_NAME)
            if stop_event.is_set():
                # Quitting was requested while getTasks() was running -
                # don't act on a now-stale result.
                break
            if not res:
                if stop_event.is_set():
                    break
                is_chrome = 'Chrome' in APP_EXE_PATH or 'chrome' in APP_EXE_PATH
                if is_chrome:
                    url = getattr(settings, 'appURL', '')
                    if _IS_WIN:
                        subprocess.Popen(
                            f'start chrome {url} --start-fullscreen --kiosk '
                            '--disable-pinch --overscroll-history-navigation=0',
                            shell=True)
                    elif _IS_MAC:
                        subprocess.Popen(
                            ['open', '-a', 'Google Chrome', '--args', url,
                             '--start-fullscreen', '--kiosk'])
                    else:
                        subprocess.Popen(
                            ['google-chrome', '--kiosk', url])
                else:
                    path = os.path.join(APP_EXE_PATH, APP_EXE_NAME)
                    cmd = [path] + APP_EXE_PARAMS
                    print(f'Starting: {" ".join(cmd)}')
                    if _IS_WIN:
                        info = subprocess.STARTUPINFO()
                        info.dwFlags    = subprocess.STARTF_USESHOWWINDOW
                        info.wShowWindow = 3  # SW_MAXIMIZE
                        subprocess.Popen(cmd, startupinfo=info)
                    else:
                        subprocess.Popen(cmd)
                logging.info(f'{datetime.now()}: App Restarted')
            elif 'Not Responding' in res:
                print(f'{APP_EXE_NAME} not responding — restarting...')
                kill_app()
            # stop_event.wait() (instead of time.sleep()) returns immediately
            # once quitting is requested, instead of sleeping up to 25s first.
            stop_event.wait(25 if not res else 5)
    except Exception:
        traceback.print_exc()

# ── Main ──────────────────────────────────────────────────────────────────────
def startAllProcess():
    if settings.checkForUpdate and not NO_APP_CONFIGURED:
        archive_update.checkUpdateStatus()

    quit_event = Event()
    stop_event = Event()
    # Nothing to launch/monitor with no app configured - skip the monitor
    # thread entirely rather than have it loop over an empty APP_EXE_NAME.
    task_thread = None if NO_APP_CONFIGURED else Thread(
        target=getTaskProcess, args=(stop_event,), daemon=True
    )

    def on_quit():
        # Called from the keyboard hotkey's own listener thread (or from
        # Ctrl+C on the main thread) - only signal here, don't do cleanup
        # or touch Tk directly. Tk (used by show_lock_window) isn't
        # thread-safe, so the lock window polls quit_event itself and
        # destroys itself on the main thread; all the actual cleanup below
        # runs exactly once, after whichever wait mechanism returns.
        print('Ctrl+Shift+S pressed — quitting...')
        quit_event.set()

    try:
        import keyboard
        keyboard.add_hotkey('ctrl+shift+s', on_quit)
        _hotkey_ok = True
    except Exception as e:
        print(f'Hotkey not available ({e}) — use Ctrl+C to quit.')
        _hotkey_ok = False

    use_lock_window = _IS_WIN and (NO_APP_CONFIGURED or lock_behind_app)
    if task_thread and not use_lock_window:
        task_thread.start()

    try:
        if use_lock_window:
            # Blocks (own Tk loop) until quit_event is set. With an app, the
            # monitor thread is started once the window is up, so the app's
            # window opens in front of it.
            show_lock_window(
                quit_event,
                behind_app=not NO_APP_CONFIGURED,
                on_ready=task_thread.start if task_thread else None,
            )
        elif _hotkey_ok:
            quit_event.wait()
        else:
            while not quit_event.is_set():
                time.sleep(1)
    except KeyboardInterrupt:
        quit_event.set()

    # Cleanup - runs once, on the main thread, regardless of which wait
    # mechanism above returned. Tell the monitor thread to stop *before*
    # killing anything, and wait for it to actually notice - otherwise it
    # can see the app missing right after kill_app() and relaunch it
    # before we exit.
    stop_event.set()
    if task_thread and task_thread.ident is not None:  # may never have started
        task_thread.join(timeout=5)
    restore_desktop()
    kill_app()
    kill_pulse()

if __name__ == '__main__':
    import traceback
    try:
        if check_app_exists():
            initApp()
            startAllProcess()
    except Exception:
        traceback.print_exc()
        _log_file.flush()
