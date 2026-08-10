# report_status.py v2.0
# Neuronic 2025

import os
import sys
import time
import json
import socket
import ctypes
import urllib.request
import urllib.parse
from ctypes import windll
from datetime import datetime

import keyboard
import audit_setting

# ── Setup ─────────────────────────────────────────────────────────────────────

host_name  = socket.gethostname()
host_ip    = socket.gethostbyname(host_name)
pulse_url  = f"https://zapsheets.com/app/{audit_setting.sheetID}/pulseboard/pulse"

console = ctypes.windll.kernel32.GetConsoleWindow()

# ── Crash log ─────────────────────────────────────────────────────────────────

crash_file = os.path.join(audit_setting.appPath, audit_setting.appName, 'crash.log')

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
        'tab':     audit_setting.sheetName,
        'exhibit': audit_setting.exhibitName,
        'host':    host_name,
        'ip':      host_ip,
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
            print(f"Pulse sent: {payload.get('status', '(no status)')}  {payload['time']}")
        else:
            print(f"Server error: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"Warning: could not reach server ({e})")

# ── Process check ─────────────────────────────────────────────────────────────

def is_running():
    for line in os.popen('tasklist').read().splitlines():
        if audit_setting.appEXEName in line:
            return line
    return ''

# ── Main monitoring loop ──────────────────────────────────────────────────────

print(f"Monitoring {audit_setting.exhibitName} → {pulse_url}")

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
