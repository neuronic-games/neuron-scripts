# guard.py v3.1
# Neuronic 2025
# Cross-platform: Windows kiosk features active on Windows only.

import os, sys

_IS_WIN = sys.platform == 'win32'
_IS_MAC = sys.platform == 'darwin'

# ── Logging: set up first so import errors are captured ──────────────────────
# guard.log keeps previous runs (each starts with a ==== line), so a crash
# isn't lost when guard is relaunched. Once it passes ~1 MB it's moved to
# guard.log.1 (replacing the older one) and a fresh guard.log is started.
# Every line starts with the date and time.
if __name__ == '__main__':
    import time as _time
    _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guard.log')
    try:
        if os.path.getsize(_log_path) > 1_000_000:
            os.replace(_log_path, _log_path + '.1')
    except OSError:
        pass
    _log_file = open(_log_path, 'a', buffering=1)
    class _Tee:
        def __init__(self, *streams):
            self.streams = streams
            self.at_line_start = True
        def write(self, data):
            if not data:
                return
            parts = []
            for line in data.splitlines(keepends=True):
                if self.at_line_start:
                    parts.append(_time.strftime('%Y-%m-%d %H:%M:%S  '))
                parts.append(line)
                self.at_line_start = line.endswith('\n')
            data = ''.join(parts)
            for s in self.streams:
                try:
                    s.write(data)
                except UnicodeEncodeError:
                    s.write(data.encode('ascii', errors='replace').decode('ascii'))
        def flush(self):
            for s in self.streams: s.flush()
    sys.stdout = _Tee(sys.__stdout__, _log_file)
    sys.stderr = _Tee(sys.__stderr__, _log_file)
    # If Python itself crashes (e.g. an access violation in Windows code
    # called through ctypes or Tk), the process dies instantly with no
    # traceback. faulthandler still writes what every thread was doing at
    # that moment into guard.log ("Windows fatal exception: ...").
    import faulthandler
    faulthandler.enable(file=_log_file, all_threads=True)
    print('=' * 60)
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
    from ctypes import wintypes

    # Win32 structures and function signatures, defined once here. (They
    # used to be defined inside the functions that use them, on every call;
    # with the start screen and the app monitor calling them from different
    # threads, one call could swap the signature out from under another:
    # "expected LP_PROCESSENTRY32W instance instead of pointer to
    # PROCESSENTRY32W".)
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)]

    class MONITORINFO(ctypes.Structure):          # MONITORINFOEXW
        _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD),
                    ('szDevice', ctypes.c_wchar * 32)]

    # For display names like "INSIGNIA-TV" (QueryDisplayConfig).
    class LUID(ctypes.Structure):
        _fields_ = [('LowPart', wintypes.DWORD), ('HighPart', wintypes.LONG)]

    class DISPLAYCONFIG_PATH_INFO(ctypes.Structure):
        _fields_ = [('srcAdapter', LUID), ('srcId', ctypes.c_uint32),
                    ('srcModeIdx', ctypes.c_uint32), ('srcFlags', ctypes.c_uint32),
                    ('tgtAdapter', LUID), ('tgtId', ctypes.c_uint32),
                    ('tgtModeIdx', ctypes.c_uint32), ('outputTechnology', ctypes.c_uint32),
                    ('rotation', ctypes.c_uint32), ('scaling', ctypes.c_uint32),
                    ('refreshNum', ctypes.c_uint32), ('refreshDen', ctypes.c_uint32),
                    ('scanLineOrdering', ctypes.c_uint32), ('targetAvailable', wintypes.BOOL),
                    ('tgtFlags', ctypes.c_uint32), ('flags', ctypes.c_uint32)]

    class DISPLAYCONFIG_MODE_INFO(ctypes.Structure):
        _fields_ = [('raw', ctypes.c_byte * 64)]

    class DISPLAYCONFIG_DEVICE_INFO_HEADER(ctypes.Structure):
        _fields_ = [('type', ctypes.c_uint32), ('size', ctypes.c_uint32),
                    ('adapterId', LUID), ('id', ctypes.c_uint32)]

    class DISPLAYCONFIG_SOURCE_DEVICE_NAME(ctypes.Structure):
        _fields_ = [('header', DISPLAYCONFIG_DEVICE_INFO_HEADER),
                    ('viewGdiDeviceName', ctypes.c_wchar * 32)]

    class DISPLAYCONFIG_TARGET_DEVICE_NAME(ctypes.Structure):
        _fields_ = [('header', DISPLAYCONFIG_DEVICE_INFO_HEADER),
                    ('flags', ctypes.c_uint32), ('outputTechnology', ctypes.c_uint32),
                    ('edidManufactureId', ctypes.c_uint16), ('edidProductCodeId', ctypes.c_uint16),
                    ('connectorInstance', ctypes.c_uint32),
                    ('monitorFriendlyDeviceName', ctypes.c_wchar * 64),
                    ('monitorDevicePath', ctypes.c_wchar * 128)]


    windll.kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    windll.kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    windll.kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    windll.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    windll.user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]

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

# Windows: if the app's process is running but none of its windows has
# been on screen for this many seconds (minimized and won't come back,
# crashed leaving the process behind...), guard.py kills and restarts it.
# Also the time a newly started app gets to open its window. 0 = off.
APP_WINDOW_TIMEOUT = int(getattr(settings, 'appWindowTimeout', 60))

# Windows: if set, the app counts as "ready" once one of its windows has a
# title containing this text (e.g. "LICM TV Studio Record"). If it isn't
# ready APP_READY_TIMEOUT seconds after starting - stuck on its loading
# window, e.g. because OBS's virtual camera didn't start - guard.py
# restarts OBS (if startObs) and the app. Gives up after 3 tries in a row,
# so a real fault doesn't make it restart forever. Blank = off.
APP_READY_TITLE   = str(getattr(settings, 'appReadyWindowTitle', '') or '').strip()
APP_READY_TIMEOUT = int(getattr(settings, 'appReadyTimeout', 180))
APP_READY_TRIES   = 3

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
    kernel32 = windll.kernel32
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
    """[(x, y, width, height, is_primary, device), ...] for every display,
    primary first (device is e.g. '\\\\.\\DISPLAY2'). Falls back to just the
    primary screen if enumeration fails."""
    from ctypes import wintypes
    user32 = windll.user32
    rects = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                         ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def _cb(hmon, _hdc, _rect, _):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, byref(info)):
            r = info.rcMonitor
            rects.append((r.left, r.top, r.right - r.left, r.bottom - r.top,
                          bool(info.dwFlags & 1),  # MONITORINFOF_PRIMARY
                          info.szDevice))
        return True

    try:
        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
    except Exception as e:
        print(f'Could not list displays ({e}) - covering the main one only.')
    if not rects:
        rects = [(0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1), True, '')]
    rects.sort(key=lambda r: not r[4])
    return rects


def _display_names():
    """{'\\\\.\\DISPLAY2': 'INSIGNIA-TV', ...} - the monitors' own names, as
    Windows Settings (and OBS) show them. {} if they can't be read."""
    names = {}
    try:
        user32 = windll.user32
        n_paths, n_modes = ctypes.c_uint32(), ctypes.c_uint32()
        if user32.GetDisplayConfigBufferSizes(2, byref(n_paths), byref(n_modes)):  # QDC_ONLY_ACTIVE_PATHS
            return names
        paths = (DISPLAYCONFIG_PATH_INFO * n_paths.value)()
        modes = (DISPLAYCONFIG_MODE_INFO * n_modes.value)()
        if user32.QueryDisplayConfig(2, byref(n_paths), paths, byref(n_modes), modes, None):
            return names
        for path in paths[:n_paths.value]:
            src = DISPLAYCONFIG_SOURCE_DEVICE_NAME()
            src.header.type, src.header.size = 1, ctypes.sizeof(src)  # GET_SOURCE_NAME
            src.header.adapterId, src.header.id = path.srcAdapter, path.srcId
            tgt = DISPLAYCONFIG_TARGET_DEVICE_NAME()
            tgt.header.type, tgt.header.size = 2, ctypes.sizeof(tgt)  # GET_TARGET_NAME
            tgt.header.adapterId, tgt.header.id = path.tgtAdapter, path.tgtId
            if (user32.DisplayConfigGetDeviceInfo(byref(src)) == 0 and
                    user32.DisplayConfigGetDeviceInfo(byref(tgt)) == 0):
                names[src.viewGdiDeviceName] = tgt.monitorFriendlyDeviceName or '(unnamed)'
    except Exception:
        pass
    return names


def _describe_display(rect, names):
    x, y, w, h, primary, device = rect
    label = names.get(device) or device.replace('\\\\.\\', '') or 'display'
    short = device.replace('\\\\.\\', '')
    if short and short != label:
        label += f' ({short})'
    return f'{label} {w}x{h} at {x},{y}' + (', main display' if primary else '')


def log_display_changes(old, new):
    names = _display_names()
    for rect in old:
        if rect not in new:
            print(f'  Display gone:  {_describe_display(rect, names)}')
    for rect in new:
        if rect not in old:
            print(f'  Display added: {_describe_display(rect, names)}')


def _zorder_around_desktop(ours):
    """Look at the window stack (front to back) around the desktop.
    Returns (lowest, ours_behind_desktop):
      lowest - the bottom-most window on screen *above* the desktop:
               visible, non-empty, not always-on-top (those stay above us
               anyway, and inserting below one would make our window
               always-on-top too), and not one of ours. 0 if none - e.g.
               after "Show desktop" (Win+D), which brings the desktop
               itself in front of every other window.
      ours_behind_desktop - True if any of our windows is behind the
               desktop (Progman / WorkerW), i.e. not visible."""
    from ctypes import wintypes
    user32 = windll.user32
    user32.GetWindowLongW.argtypes = [wintypes.HWND, c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, c_int]
    ours = set(ours)
    found = {'lowest': 0, 'desktop': False, 'behind': False}
    cls = ctypes.create_unicode_buffer(64)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _):
        if hwnd in ours:
            if found['desktop']:
                found['behind'] = True
            return True
        if found['desktop'] or not user32.IsWindowVisible(hwnd):
            return True
        user32.GetClassNameW(hwnd, cls, 64)
        if cls.value in ('Progman', 'WorkerW'):
            found['desktop'] = True   # everything after this is behind it
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x8:  # WS_EX_TOPMOST
            return True
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, byref(r))
        if r.right - r.left > 0 and r.bottom - r.top > 0:
            found['lowest'] = hwnd
        return True

    user32.EnumWindows(_cb, 0)
    return found['lowest'], found['behind']


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
             'app_hwnd': 0, 'ticks': 0, 'was_behind': False}
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

    first_build = [True]

    def _build():
        for top in state['tops']:
            top.destroy()
        state['monitors'] = _monitor_rects()
        state['tops'], state['hwnds'], state['screens'] = [], [], []
        for x, y, w, h, primary, _device in state['monitors']:
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
        if first_build[0]:
            first_build[0] = False
            names = _display_names()
            for rect in state['monitors']:
                print(f'  Display: {_describe_display(rect, names)}')

    def _send_to_bottom():
        """Keep our windows just above the desktop: below every other
        window, but never behind the desktop itself."""
        ours = state['hwnds']
        lowest, behind = _zorder_around_desktop(ours)
        if behind and not state['was_behind']:
            print('Start screen was behind the desktop - moving it back in front of it.')
        state['was_behind'] = behind
        if lowest:
            user32.SetWindowPos(ours[0], lowest, 0, 0, 0, 0, SWP_FLAGS)
        else:
            # No window above the desktop (e.g. "Show desktop" brought the
            # desktop to the front): go to the front of the normal
            # (not always-on-top) windows, which puts us above the desktop.
            user32.SetWindowPos(ours[0], 0, 0, 0, 0, 0, SWP_FLAGS)  # HWND_TOP
        for prev, hwnd in zip(ours, ours[1:]):
            user32.SetWindowPos(hwnd, prev, 0, 0, 0, 0, SWP_FLAGS)

    def _watch_app():
        # Only windows actually on screen count - a minimized app leaves
        # the start screen showing, so keep it animating.
        windows, _minimized = _app_windows(_pids_named(APP_EXE_NAME))
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
            hide_taskbars()
            if state['ticks'] % 5 == 0:
                current = _monitor_rects()
                if current != state['monitors']:
                    print('Displays changed - rebuilding the lock screen.')
                    log_display_changes(state['monitors'], current)
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
        show_taskbars()

def _taskbars():
    """Every taskbar window: the main one (Shell_TrayWnd) plus one
    Shell_SecondaryTrayWnd per extra display when Windows shows the
    taskbar on all displays."""
    from ctypes import wintypes
    user32 = windll.user32
    user32.FindWindowExW.restype = wintypes.HWND
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND,
                                     wintypes.LPCWSTR, wintypes.LPCWSTR]
    bars = []
    main = user32.FindWindowExW(None, None, 'Shell_TrayWnd', None)
    if main:
        bars.append(main)
    hwnd = None
    while True:
        hwnd = user32.FindWindowExW(None, hwnd, 'Shell_SecondaryTrayWnd', None)
        if not hwnd:
            break
        bars.append(hwnd)
    return bars

def hide_taskbars():
    """Hide every taskbar that's showing. Called at start and then
    regularly, because Windows brings taskbars back on its own (a display
    reconnected, Explorer restarted...)."""
    if not _IS_WIN:
        return
    from ctypes import wintypes
    user32 = windll.user32
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, c_int]
    for bar in _taskbars():
        if user32.IsWindowVisible(bar):
            user32.ShowWindow(bar, 0)  # SW_HIDE

def show_taskbars():
    from ctypes import wintypes
    windll.user32.ShowWindow.argtypes = [wintypes.HWND, c_int]
    for bar in _taskbars():
        windll.user32.ShowWindow(bar, 5)  # SW_SHOW

# ── Init ──────────────────────────────────────────────────────────────────────
def log_boot_time():
    """Log when the computer last started, so a reboot is easy to tell
    apart from Launch simply being run again."""
    try:
        if _IS_WIN:
            windll.kernel32.GetTickCount64.restype = ctypes.c_uint64
            uptime = windll.kernel32.GetTickCount64() / 1000
        else:
            with open('/proc/uptime') as f:
                uptime = float(f.read().split()[0])
    except Exception as e:
        print(f'Could not read when the computer started: {e}')
        return
    booted = datetime.fromtimestamp(time.time() - uptime).strftime('%Y-%m-%d %H:%M')
    mins = int(uptime // 60)
    ago = f'{mins} min' if mins < 120 else f'{mins // 60} h {mins % 60} min'
    note = ' - this start follows a reboot' if uptime < 10 * 60 else ''
    print(f'Computer started {booted} ({ago} ago){note}.')

def initApp():
    initApp.isStarted = False
    log_boot_time()
    kill_app()
    if _IS_WIN:
        initApp.consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
        hide_taskbars()
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
    """Linux/macOS: the app's process list from pgrep, or '' if it isn't
    running. (Windows uses _pids_named() / _app_windows() instead.)"""
    try:
        result = subprocess.run(['pgrep', '-f', name], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ''

def _app_windows(pids):
    """(shown, minimized): the app's visible, non-empty top-level windows
    (always-on-top ones included), split into those actually on screen and
    those minimized."""
    from ctypes import wintypes
    user32 = windll.user32
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.IsIconic.argtypes = [wintypes.HWND]
    shown, minimized = [], []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        if pid.value not in pids:
            return True
        if user32.IsIconic(hwnd):
            minimized.append(hwnd)
            return True
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, byref(r))
        if r.right - r.left > 0 and r.bottom - r.top > 0:
            shown.append(hwnd)
        return True

    user32.EnumWindows(_cb, 0)
    return shown, minimized

# Windows exit codes that mean the app crashed, with a plain description.
_CRASH_CODES = {
    0xC0000005: 'access violation',
    0xC0000409: 'stack buffer overrun / fail-fast',
    0xC00000FD: 'stack overflow',
    0xC0000374: 'heap corruption',
    0xC000001D: 'illegal instruction',
    0xC0000094: 'integer divide by zero',
    0xC0000135: 'missing DLL',
    0xC0000142: 'DLL failed to initialise',
    0xC000041D: 'unhandled exception in a callback',
    0x80000003: 'breakpoint',
    0xE0434352: 'unhandled .NET exception',
}

def describe_exit(code):
    """A plain-English guess at why the app exited, from its exit code."""
    if code is None:
        return 'exit code unknown'
    u = code & 0xFFFFFFFF
    if u == 0:
        return 'exit code 0 - it closed normally (the app quit itself, e.g. its own quit key or Alt+F4)'
    if u == 1:
        return 'exit code 1 - usually a forced kill (Task Manager / taskkill), or the app reporting an error'
    if u in _CRASH_CODES:
        return f'exit code 0x{u:08X} - CRASHED ({_CRASH_CODES[u]})'
    if u >= 0xC0000000:
        return f'exit code 0x{u:08X} - CRASHED (Windows error code)'
    return f'exit code {code}'

def start_app():
    """Start the app. Returns the Popen handle (so its exit code can be
    logged later), or None for Chrome, which is started via the shell."""
    is_chrome = 'Chrome' in APP_EXE_PATH or 'chrome' in APP_EXE_PATH
    if is_chrome:
        url = getattr(settings, 'appURL', '')
        print(f'Starting Chrome kiosk: {url}')
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
            subprocess.Popen(['google-chrome', '--kiosk', url])
    else:
        path = os.path.join(APP_EXE_PATH, APP_EXE_NAME)
        cmd = [path] + APP_EXE_PARAMS
        print(f'Starting: {" ".join(cmd)}')
        if _IS_WIN:
            info = subprocess.STARTUPINFO()
            info.dwFlags    = subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = 3  # SW_MAXIMIZE
            proc = subprocess.Popen(cmd, startupinfo=info)
        else:
            proc = subprocess.Popen(cmd)
        logging.info(f'{datetime.now()}: App Restarted')
        return proc
    logging.info(f'{datetime.now()}: App Restarted')
    return None

def _check_app_windows(watch):
    """Windows: the app's process is running - make sure it actually has a
    window on screen and isn't hung. `watch` carries state between checks.
    Returns True if the app was killed (so it gets restarted)."""
    user32 = windll.user32
    now = time.monotonic()
    shown, minimized = _app_windows(watch['pids'])

    if shown:
        watch['no_window_since'] = None
        # Hung = not handling input for 5s+ (what Task Manager calls "Not
        # Responding"). Need it on two checks in a row before killing.
        if any(user32.IsHungAppWindow(h) for h in shown):
            watch['hung_checks'] += 1
            if watch['hung_checks'] >= 2:
                print(f'{APP_EXE_NAME} not responding - restarting...')
                watch['killed_by_guard'] = 'it was not responding'
                kill_app()
                return True
        else:
            watch['hung_checks'] = 0
        return False

    watch['hung_checks'] = 0
    if watch['no_window_since'] is None:
        watch['no_window_since'] = now
    if minimized:
        # Full-screen apps (e.g. Unity) often minimize when they lose
        # focus - bring the window back.
        print(f'{APP_EXE_NAME} is minimized - restoring it.')
        for h in minimized:
            user32.ShowWindow(h, 9)  # SW_RESTORE
        user32.SetForegroundWindow(minimized[0])
    if APP_WINDOW_TIMEOUT and now - watch['no_window_since'] >= APP_WINDOW_TIMEOUT:
        print(f'{APP_EXE_NAME} is running but has had no window on screen for '
              f'{APP_WINDOW_TIMEOUT}s - restarting it.')
        watch['killed_by_guard'] = 'it had no window on screen'
        kill_app()
        return True
    return False

def _restart_obs():
    """Run start_obs.cmd (closes the app and OBS, restarts OBS with its
    virtual camera, reopens projectors) and log the end of its output."""
    path = os.path.join(_script_dir, 'start_obs.cmd')
    try:
        result = subprocess.run(['cmd', '/c', path], capture_output=True, text=True,
                                errors='replace', timeout=300, cwd=_script_dir)
        lines = [l for l in (result.stdout + result.stderr).splitlines() if l.strip()]
        for line in lines[-8:]:
            print(f'  start_obs: {line.strip()}')
    except Exception as e:
        print(f'Could not restart OBS: {e}')

def _check_app_ready(watch):
    """Windows: once the app is running, watch for its main window
    (APP_READY_TITLE). Returns True if the app was killed to restart it."""
    if not APP_READY_TITLE or watch['ready']:
        return False
    shown, _minimized = _app_windows(watch['pids'])
    for h in shown + _minimized:
        title = _window_title(h)
        if APP_READY_TITLE.lower() in title.lower():
            watch['ready'] = True
            watch['stuck_tries'] = 0
            secs = int(time.monotonic() - watch['started_at'])
            print(f'App ready ("{title}") {secs}s after starting.')
            return False
    if time.monotonic() - watch['started_at'] < APP_READY_TIMEOUT:
        return False
    if watch['stuck_tries'] >= APP_READY_TRIES:
        print(f'App still not ready after {APP_READY_TRIES} restarts - leaving it running. '
              'Check OBS (virtual camera) and the camera.')
        watch['ready'] = True  # stop retrying until the app is next restarted
        return False
    watch['stuck_tries'] += 1
    print(f'App not ready after {APP_READY_TIMEOUT}s (no "{APP_READY_TITLE}" window) - '
          f'restarting OBS and the app (try {watch["stuck_tries"]} of {APP_READY_TRIES}).')
    watch['killed_by_guard'] = 'it was stuck loading'
    kill_app()
    if getattr(settings, 'startObs', False):
        _restart_obs()
    return True

def getTaskProcess(stop_event):
    """Keep the app running. Each check runs in its own try/except, so an
    unexpected error is logged and monitoring carries on, instead of the
    app silently never being restarted again."""
    import traceback
    watch = {'pids': set(), 'no_window_since': None, 'hung_checks': 0,
             'proc': None, 'killed_by_guard': None, 'started': False,
             'started_at': 0.0, 'ready': False, 'stuck_tries': 0}
    while not stop_event.is_set():
        delay = 5
        try:
            hide_taskbars()  # Windows can bring them back on its own
            if _IS_WIN:
                # Exact process-name match (not a text search of tasklist
                # output, which also matched window titles and was slow).
                watch['pids'] = _pids_named(APP_EXE_NAME)
                running = bool(watch['pids'])
            else:
                running = bool(getTasks(APP_EXE_NAME))
            if stop_event.is_set():
                # Quitting was requested during the check - don't act on a
                # now-stale result.
                break
            if not running:
                proc = watch['proc']
                if watch['killed_by_guard']:
                    print(f'App stopped: guard.py closed it because {watch["killed_by_guard"]}.')
                elif proc is not None:
                    try:
                        code = proc.wait(timeout=2)
                    except Exception:
                        code = None
                    print(f'App stopped on its own: {describe_exit(code)}.')
                elif watch['started']:
                    print('App stopped on its own (exit code unknown for Chrome).')
                watch['killed_by_guard'] = None
                watch['proc'] = start_app()
                watch['started'] = True
                watch['started_at'] = time.monotonic()
                watch['ready'] = False
                # Give the new process time to open its window before the
                # no-window timer starts counting.
                watch['no_window_since'] = time.monotonic()
                watch['hung_checks'] = 0
                delay = 25
            elif _IS_WIN and _check_app_windows(watch):
                delay = 3  # killed - restart it on the next check
            elif _IS_WIN and _check_app_ready(watch):
                delay = 3  # stuck loading - killed, restart it on the next check
        except Exception:
            print('Error while checking the app (monitoring continues):')
            traceback.print_exc()
            delay = 10
        # stop_event.wait() (instead of time.sleep()) returns immediately
        # once quitting is requested.
        stop_event.wait(delay)

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
        print('Ctrl+Shift+S pressed - quitting...')
        quit_event.set()

    try:
        import keyboard
        keyboard.add_hotkey('ctrl+shift+s', on_quit)
        _hotkey_ok = True
    except Exception as e:
        print(f'Hotkey not available ({e}) - use Ctrl+C to quit.')
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

def _already_running():
    """True if another guard.py is already running (e.g. Launch was run
    twice at once). Uses a named mutex, which Windows frees automatically
    when the process holding it exits, however it exits."""
    if not _IS_WIN:
        return False
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    _already_running.handle = k32.CreateMutexW(None, False, 'Local\\NeuronicGuardPy')
    return ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS

if __name__ == '__main__':
    import traceback
    if _already_running():
        print('Another guard.py is already running - this one is exiting.')
        sys.exit(0)
    try:
        if check_app_exists():
            initApp()
            startAllProcess()
    except Exception:
        traceback.print_exc()
        _log_file.flush()
