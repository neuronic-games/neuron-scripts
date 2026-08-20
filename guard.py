# guard.py v3.0
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
crash_path    = getattr(settings, 'crashPath',         'crash.log')
logo_brand    = getattr(settings, 'logoBrand',         'neuronic.png')

desktop_color = getattr(settings, 'desktopColor',      RGB(0, 0, 0)) if _IS_WIN else None
reset_desktop = getattr(settings, 'resetDesktopColor', RGB(0, 0, 0)) if _IS_WIN else None

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

def show_lock_window(quit_event):
    """Full-screen, borderless, always-on-top black window with the logo
    centered, blocking any access to the desktop underneath (the
    wallpaper/desktop-color trick set in initApp() alone doesn't stop
    someone from reaching desktop icons/taskbar in every case - an actual
    covering window does). Used only when NO_APP_CONFIGURED. Runs its own
    Tk event loop on the calling thread (must be the main thread) until
    quit_event is set from elsewhere (e.g. the Ctrl+Shift+S hotkey, which
    runs on its own thread - only quit_event.set() is called from there,
    never anything Tk-related, since Tk isn't thread-safe)."""
    import tkinter as tk

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.configure(bg='black')
    root.geometry(f'{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0')

    logo_path = os.path.join(_script_dir, 'logo', logo_brand)
    image = None
    if os.path.isfile(logo_path):
        try:
            image = tk.PhotoImage(file=logo_path)
        except Exception as e:
            print(f'Could not load logo image {logo_path}: {e}')

    label = tk.Label(root, bg='black', image=image if image else None)
    label.image = image  # keep a reference - PhotoImage is GC'd otherwise
    label.place(relx=0.5, rely=0.5, anchor='center')

    def _poll_quit():
        if quit_event.is_set():
            root.destroy()
        else:
            root.after(200, _poll_quit)

    root.after(200, _poll_quit)
    root.mainloop()

def getWallpaper():
    bg = os.path.join(_script_dir, 'background')
    files = os.listdir(bg) if os.path.isdir(bg) else []
    return os.path.join(bg, files[0]) if files else ''

def restore_desktop():
    if _IS_WIN:
        ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(reset_desktop)))
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
                    print(f'Starting: {path}')
                    if _IS_WIN:
                        info = subprocess.STARTUPINFO()
                        info.dwFlags    = subprocess.STARTF_USESHOWWINDOW
                        info.wShowWindow = 3  # SW_MAXIMIZE
                        subprocess.Popen(path, startupinfo=info)
                    else:
                        subprocess.Popen([path])
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

    if task_thread:
        task_thread.start()

    try:
        if NO_APP_CONFIGURED and _IS_WIN:
            show_lock_window(quit_event)  # blocks (own Tk loop) until quit_event is set
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
    if task_thread:
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
