# report_status.py v1.1
# Neuronic 2025

import os
import sys
import time
import socket
import ctypes
from ctypes import windll
from datetime import datetime

import gspread
import keyboard
import audit_setting

# ── Google Sheets connection ──────────────────────────────────────────────────

_here     = os.path.dirname(os.path.abspath(__file__))
cred_file = os.path.join(_here, 'credentials.json')

try:
    service_account = gspread.service_account(filename=cred_file)
    workbook        = service_account.open_by_key(audit_setting.sheetID)
except Exception as e:
    msg = str(e)
    if 'invalid_grant' in msg or 'iat and exp' in msg or 'Token must be a short-lived' in msg:
        print("ERROR: Google authentication failed because this machine's clock is out of sync.")
        print("       Fix: open Settings > Time & Language > Date & Time")
        print("         and set the correct date and time manually.")
        print("       Then re-run this script.")
    elif '403' in msg or 'does not have permission' in msg or isinstance(e, PermissionError):
        try:
            import json
            sa_email = json.load(open(cred_file)).get('client_email', 'unknown')
        except Exception:
            sa_email = 'unknown'
        print(f"ERROR: The service account does not have access to sheet ID: {audit_setting.sheetID}")
        print(f"       Service account: {sa_email}")
        print("       Fix: open the sheet in Google Sheets, click Share, and add")
        print(f"         {sa_email}  with Editor access.")
    elif 'credentials.json' in msg or 'No such file' in msg:
        print("ERROR: credentials.json not found. Make sure it is in the same folder as this script.")
    else:
        print("ERROR connecting to Google Sheets:", msg)
    sys.exit(1)

sheet_name = workbook.worksheets()[0].title if audit_setting.sheetName == "" else audit_setting.sheetName
worksheet  = workbook.worksheet(sheet_name)

# ── Locate this machine's row ─────────────────────────────────────────────────

cell = worksheet.find(audit_setting.exhibitName)
if cell is None:
    print(f"ERROR: Exhibit '{audit_setting.exhibitName}' not found in sheet '{sheet_name}'.")
    sys.exit(1)
row = cell.row

# ── Hide console window ───────────────────────────────────────────────────────

console = ctypes.windll.kernel32.GetConsoleWindow()
windll.user32.ShowWindow(console, 0)

# ── Write hostname and IP on startup ─────────────────────────────────────────

host_name = socket.gethostname()
host_ip   = socket.gethostbyname(host_name)
worksheet.update(f'B{row}', host_name)
worksheet.update(f'C{row}', host_ip)
print(f"Connected: {sheet_name} / {audit_setting.exhibitName} (row {row})")
print(f"Host: {host_name}  IP: {host_ip}")

# ── Crash log helpers ─────────────────────────────────────────────────────────

crash_file = os.path.join(audit_setting.appPath, audit_setting.appName, 'crash.log')

def report_crashes():
    """Read crash log, write count and times to sheet, then clear the log."""
    if not os.path.exists(crash_file):
        return
    with open(crash_file, 'r') as f:
        lines = f.readlines()
    times = []
    for line in lines:
        try:
            t = line.split(': App Restarted')[0].split('.')[0].split(':', 2)[2].split(' ')[1]
            times.append(t)
        except IndexError:
            pass
    worksheet.update(f'F{row}', len(lines))
    worksheet.update(f'G{row}', ', '.join(times))
    open(crash_file, 'w').close()
    print(f"Crash report updated: {len(lines)} restart(s)")

report_crashes()

# ── Process check ─────────────────────────────────────────────────────────────

def is_running():
    """Return the tasklist line for the app, or empty string if not found."""
    for line in os.popen('tasklist').read().splitlines():
        if audit_setting.appEXEName in line:
            return line
    return ''

# ── Main monitoring loop ──────────────────────────────────────────────────────

print("Monitoring...")

update_counter = 0

while True:
    res = is_running()

    if not res:
        # App not running — reset so status is written again when it comes back
        update_counter = 0
        time.sleep(2)

    elif 'Not Responding' in res:
        time.sleep(2)

    else:
        update_counter += 1

        if update_counter == 1:
            # First detection after (re)start — write status to sheet
            time_str = datetime.now().strftime("%m/%d/%Y  %H:%M:%S")
            worksheet.update(f'D{row}', "Ok")
            worksheet.update(f'E{row}', time_str)
            print(f"Status updated: Ok  {time_str}")

        elif datetime.now().strftime("%H:%M:%S") == '00:00:00':
            # Daily midnight refresh
            time_str = datetime.now().strftime("%m/%d/%Y  %H:%M:%S")
            worksheet.update(f'B{row}', host_name)
            worksheet.update(f'C{row}', host_ip)
            worksheet.update(f'D{row}', "Ok")
            worksheet.update(f'E{row}', time_str)
            report_crashes()

        # Win+Shift+D to exit
        if keyboard.is_pressed("left windows") and keyboard.is_pressed("shift") and keyboard.is_pressed("d"):
            windll.user32.DestroyWindow(console)
            break

        time.sleep(5)
