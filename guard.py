# guard.py v2.0
# Neuronic 2025

import os, sys

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

import time, subprocess, logging, ctypes, keyboard
from datetime import datetime
from threading import Thread
from ctypes import byref, c_int, windll
from ctypes.wintypes import RGB
import settings
import archive_update

# ── Settings ──────────────────────────────────────────────────────────────────
APP_EXE_PATH  = getattr(settings, 'appEXEPath',        r'C:/Program Files/Google/Chrome/Application')
APP_EXE_NAME  = getattr(settings, 'appEXEName',        'chrome.exe')
crash_path    = getattr(settings, 'crashPath',         'crash.log')
desktop_color = getattr(settings, 'desktopColor',      RGB(0, 0, 0))
reset_desktop = getattr(settings, 'resetDesktopColor', RGB(0, 0, 0))
logo_brand    = getattr(settings, 'logoBrand',         'neuronic.png')

_script_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(_script_dir, crash_path),
    filemode='w', level=logging.INFO,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def getWallpaper():
    bg = os.path.join(_script_dir, 'background')
    files = os.listdir(bg) if os.path.isdir(bg) else []
    return os.path.join(bg, files[0]) if files else ''

def restore_desktop():
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(reset_desktop)))
    wp = getWallpaper()
    if wp:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, wp, 3)
    windll.user32.ShowWindow(initApp.taskBarStatus, 9)

# ── Init ──────────────────────────────────────────────────────────────────────
def initApp():
    initApp.isStarted    = False
    initApp.taskBarStatus    = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    initApp.consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
    windll.user32.ShowWindow(initApp.taskBarStatus, 0)
    windll.user32.ShowWindow(initApp.consoleBarHandler, 0)
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(desktop_color)))
    logo_path = os.path.join(_script_dir, 'logo', logo_brand)
    ctypes.windll.user32.SystemParametersInfoW(20, 0, logo_path, 3)
    print('Checking status periodically...')

# ── App monitor ───────────────────────────────────────────────────────────────
def getTasks(name):
    for line in os.popen('tasklist /v').read().strip().split('\n'):
        if name in line:
            return line
    return ''

def getTaskProcess():
    import traceback
    try:
        while True:
            res = getTasks(APP_EXE_NAME)
            if not res:
                if 'Chrome' in APP_EXE_PATH:
                    url = settings.appPath
                    cmd = (f'start chrome {url} --start-fullscreen --kiosk '
                           '--disable-pinch --overscroll-history-navigation=0')
                    subprocess.Popen(cmd, shell=True)
                else:
                    path = os.path.join(APP_EXE_PATH, APP_EXE_NAME)
                    print(f'Starting: {path}')
                    info = subprocess.STARTUPINFO()
                    info.dwFlags = subprocess.STARTF_USESHOWWINDOW
                    info.wShowWindow = 3  # SW_MAXIMIZE
                    subprocess.Popen(path, startupinfo=info)
                logging.info(f'{datetime.now()}: App started')
            elif 'Not Responding' in res:
                print(f'{APP_EXE_NAME} not responding — restarting...')
                os.system(f'taskkill /im "{APP_EXE_NAME}" /f')
            time.sleep(25 if not res else 5)
    except Exception:
        traceback.print_exc()

# ── Main ──────────────────────────────────────────────────────────────────────
def startAllProcess():
    if settings.checkForUpdate:
        archive_update.checkUpdateStatus()

    task_thread = Thread(target=getTaskProcess, daemon=True)
    task_thread.start()

    try:
        while True:
            if keyboard.is_pressed('ctrl+shift+s'):
                restore_desktop()
                os.system(f'taskkill /im "{APP_EXE_NAME}" /f')
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        restore_desktop()
        os.system(f'taskkill /im "{APP_EXE_NAME}" /f')

if __name__ == '__main__':
    import traceback
    try:
        initApp()
        startAllProcess()
    except Exception:
        traceback.print_exc()
        _log_file.flush()
