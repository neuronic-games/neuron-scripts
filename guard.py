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

_script_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(_script_dir, crash_path),
    filemode='w', level=logging.INFO,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def kill_app():
    if _IS_WIN:
        os.system(f'taskkill /im "{APP_EXE_NAME}" /f >nul 2>&1')
    else:
        subprocess.run(['pkill', '-f', APP_EXE_NAME], capture_output=True)

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

def getTaskProcess():
    import traceback
    try:
        while True:
            res = getTasks(APP_EXE_NAME)
            if not res:
                is_chrome = 'Chrome' in APP_EXE_PATH or 'chrome' in APP_EXE_PATH
                if is_chrome:
                    url = getattr(settings, 'appPath', '')
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
                logging.info(f'{datetime.now()}: App started')
            elif 'Not Responding' in res:
                print(f'{APP_EXE_NAME} not responding — restarting...')
                kill_app()
            time.sleep(25 if not res else 5)
    except Exception:
        traceback.print_exc()

# ── Main ──────────────────────────────────────────────────────────────────────
def startAllProcess():
    if settings.checkForUpdate:
        archive_update.checkUpdateStatus()

    quit_event = Event()

    def on_quit():
        print('Ctrl+Shift+S pressed — quitting...')
        restore_desktop()
        kill_app()
        quit_event.set()

    try:
        import keyboard
        keyboard.add_hotkey('ctrl+shift+s', on_quit)
        _hotkey_ok = True
    except Exception as e:
        print(f'Hotkey not available ({e}) — use Ctrl+C to quit.')
        _hotkey_ok = False

    task_thread = Thread(target=getTaskProcess, daemon=True)
    task_thread.start()

    try:
        if _hotkey_ok:
            quit_event.wait()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        on_quit()

if __name__ == '__main__':
    import traceback
    try:
        initApp()
        startAllProcess()
    except Exception:
        traceback.print_exc()
        _log_file.flush()
