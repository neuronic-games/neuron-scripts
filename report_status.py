# report_status.py v2.0
# Neuronic 2025

import os
import sys
import time
import json
import socket
import ctypes
import platform
import urllib.request
import urllib.parse
from ctypes import windll
from datetime import datetime

import keyboard
import settings

# ── Setup ─────────────────────────────────────────────────────────────────────

host_name  = socket.gethostname()
host_ip    = socket.gethostbyname(host_name)
pulse_url  = f"https://zapsheets.com/app/{settings.sheetID}/pulseboard/pulse"

console = ctypes.windll.kernel32.GetConsoleWindow()

# ── System info ───────────────────────────────────────────────────────────────

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength',                ctypes.c_ulong),
        ('dwMemoryLoad',            ctypes.c_ulong),
        ('ullTotalPhys',            ctypes.c_ulonglong),
        ('ullAvailPhys',            ctypes.c_ulonglong),
        ('ullTotalPageFile',        ctypes.c_ulonglong),
        ('ullAvailPageFile',        ctypes.c_ulonglong),
        ('ullTotalVirtual',         ctypes.c_ulonglong),
        ('ullAvailVirtual',         ctypes.c_ulonglong),
        ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
    ]

def get_os():
    try:
        ver   = platform.version().split('.')
        build = int(ver[2]) if len(ver) >= 3 else 0
        name  = 'Windows 11' if build >= 22000 else f'Windows {platform.release()}'
        return f'{name} (build {build})'
    except Exception:
        return platform.system()

def get_memory():
    try:
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        free_gb  = mem.ullAvailPhys / (1024 ** 3)
        total_gb = mem.ullTotalPhys / (1024 ** 3)
        return f'{free_gb:.1f}/{total_gb:.0f} GB'
    except Exception:
        return ''

def get_disk():
    try:
        drive = (os.path.splitdrive(settings.appPath)[0] or 'C:') + '\\'
        free  = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive, None, ctypes.byref(total), ctypes.byref(free))
        free_gb  = free.value  / (1024 ** 3)
        total_gb = total.value / (1024 ** 3)
        return f'{free_gb:.0f}/{total_gb:.0f} GB'
    except Exception:
        return ''

def get_uptime():
    try:
        ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
        ms   = ctypes.windll.kernel32.GetTickCount64()
        secs = ms // 1000
        h, secs = divmod(secs, 3600)
        m, s    = divmod(secs, 60)
        return f'{h:02d}:{m:02d}:{s:02d}'
    except Exception:
        return ''

def get_last_reboot():
    try:
        from datetime import timedelta
        ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
        ms = ctypes.windll.kernel32.GetTickCount64()
        reboot = datetime.now() - timedelta(milliseconds=ms)
        return reboot.strftime('%m/%d %H:%M')
    except Exception:
        return ''

# ── Crash log ─────────────────────────────────────────────────────────────────

crash_file = os.path.join(settings.appPath, settings.appName, 'crash.log')

def read_and_clear_crashes():
    """Return (count, times_str) from the crash log and clear it."""
    if not os.path.exists(crash_file):
        return 0, ''
    with open(crash_file, 'r') as f:
        lines = f.readlines()
    times = []
    for line in lines:
        try:
            t = line.split(': App Restarted')[0].split('.')[0].split(':', 2)[2].split(' ')[1]
            times.append(t)
        except IndexError:
            pass
    open(crash_file, 'w').close()
    return len(lines), ', '.join(times)

# ── Send heartbeat to server ──────────────────────────────────────────────────

def send_pulse(status='', include_crashes=False):
    payload = {
        'tab':     settings.sheetName,
        'exhibit': settings.exhibitName,
        'host':    host_name,
        'ip':      host_ip,
        'os':          get_os(),
        'memory':      get_memory(),
        'disk':        get_disk(),
        'uptime':      get_uptime(),
        'last_reboot': get_last_reboot(),
        'time':    datetime.now().strftime("%m/%d/%Y  %H:%M:%S"),
    }
    if status:
        payload['status'] = status
    if include_crashes:
        crashes, crash_times = read_and_clear_crashes()
        payload['crashes']     = crashes
        payload['crash_times'] = crash_times

    data = urllib.parse.urlencode(payload).encode()
    try:
        with urllib.request.urlopen(pulse_url, data, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get('ok'):
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Pulse OK")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Server error: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"Warning: could not reach server ({e})")

# ── Process check ─────────────────────────────────────────────────────────────

def is_running():
    for line in os.popen('tasklist').read().splitlines():
        if settings.appEXEName in line:
            return line
    return ''

# ── Main monitoring loop ──────────────────────────────────────────────────────

print(f"Monitoring {settings.exhibitName} → {pulse_url}")

# On startup: record host/IP and clear any previous crash log
send_pulse(include_crashes=True)

update_counter = 0

while True:
    res = is_running()

    if not res:
        # App not running — reset so we send Ok again when it comes back
        update_counter = 0
        time.sleep(2)

    elif 'Not Responding' in res:
        time.sleep(2)

    else:
        update_counter += 1

        if update_counter == 1:
            # App just started or restarted
            send_pulse(status='Ok')

        elif datetime.now().strftime("%H:%M:%S") == '00:00:00':
            # Daily midnight refresh — include crash count for the day
            send_pulse(status='Ok', include_crashes=True)

        # Win+Shift+D to exit
        if keyboard.is_pressed("left windows") and keyboard.is_pressed("shift") and keyboard.is_pressed("d"):
            windll.user32.DestroyWindow(console)
            break

        time.sleep(5)
