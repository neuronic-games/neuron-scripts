# pulse.py v3.0
# Report a pulse to PulseBoard. Cross-platform: Windows, macOS, Linux.
# Neuronic 2025

import os, sys, time, json, socket, platform, subprocess, shutil
import urllib.request, urllib.parse
from datetime import datetime, timedelta

import settings

_IS_WIN = sys.platform == 'win32'
_IS_MAC = sys.platform == 'darwin'

# ── Setup ─────────────────────────────────────────────────────────────────────

host_name = socket.gethostname()
host_ip   = socket.gethostbyname(host_name)
pulse_url = f"https://zapsheets.com/app/{settings.sheetID}/pulseboard/pulse"

# ── System info ───────────────────────────────────────────────────────────────

def get_os():
    try:
        if _IS_WIN:
            ver   = platform.version().split('.')
            build = int(ver[2]) if len(ver) >= 3 else 0
            name  = 'Windows 11' if build >= 22000 else f'Windows {platform.release()}'
            return f'{name} (build {build})'
        elif _IS_MAC:
            return f'macOS {platform.mac_ver()[0]}'
        else:
            return f'{platform.system()} {platform.release()}'
    except Exception:
        return platform.system()

def get_memory():
    try:
        if _IS_WIN:
            import ctypes
            class MEMSTATEX(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                             ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                             ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                             ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                             ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
            mem = MEMSTATEX()
            mem.dwLength = ctypes.sizeof(MEMSTATEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            free_gb  = mem.ullAvailPhys / (1024 ** 3)
            total_gb = mem.ullTotalPhys  / (1024 ** 3)
        elif _IS_MAC:
            total_bytes = int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode().strip())
            vm = subprocess.check_output(['vm_stat']).decode()
            page_size = 4096
            free_pages = 0
            for line in vm.splitlines():
                if 'Pages free' in line or 'Pages inactive' in line:
                    free_pages += int(line.split(':')[1].strip().rstrip('.'))
            total_gb = total_bytes / (1024 ** 3)
            free_gb  = (free_pages * page_size) / (1024 ** 3)
        else:  # Linux
            info = {}
            with open('/proc/meminfo') as f:
                for line in f:
                    k, v = line.split(':')
                    info[k.strip()] = int(v.strip().split()[0]) * 1024
            total_gb = info['MemTotal']     / (1024 ** 3)
            free_gb  = info['MemAvailable'] / (1024 ** 3)
        return f'{free_gb:.1f}/{total_gb:.0f} GB'
    except Exception:
        return ''

def get_disk():
    try:
        path = getattr(settings, 'appPath', os.path.expanduser('~'))
        usage = shutil.disk_usage(path)
        free_gb  = usage.free  / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        return f'{free_gb:.0f}/{total_gb:.0f} GB'
    except Exception:
        return ''

def get_uptime():
    try:
        if _IS_WIN:
            import ctypes
            ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
            secs = ctypes.windll.kernel32.GetTickCount64() // 1000
        elif _IS_MAC:
            import re, time as _t
            out = subprocess.check_output(['sysctl', '-n', 'kern.boottime']).decode()
            m = re.search(r'sec\s*=\s*(\d+)', out)
            secs = int(_t.time()) - int(m.group(1)) if m else 0
        else:  # Linux
            with open('/proc/uptime') as f:
                secs = int(float(f.read().split()[0]))
        h, rem = divmod(secs, 3600)
        m, s   = divmod(rem, 60)
        return f'{h:02d}:{m:02d}:{s:02d}'
    except Exception:
        return ''

def get_last_reboot():
    try:
        if _IS_WIN:
            import ctypes
            ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
            ms     = ctypes.windll.kernel32.GetTickCount64()
            reboot = datetime.now() - timedelta(milliseconds=ms)
        elif _IS_MAC:
            import re, time as _t
            out = subprocess.check_output(['sysctl', '-n', 'kern.boottime']).decode()
            m = re.search(r'sec\s*=\s*(\d+)', out)
            reboot = datetime.fromtimestamp(int(m.group(1))) if m else datetime.now()
        else:  # Linux
            with open('/proc/uptime') as f:
                reboot = datetime.now() - timedelta(seconds=float(f.read().split()[0]))
        return reboot.strftime('%m/%d %H:%M')
    except Exception:
        return ''

# ── TeamViewer ID ─────────────────────────────────────────────────────────────

def get_teamviewer_id():
    if _IS_WIN:
        try:
            import winreg
            for path in [r'SOFTWARE\WOW6432Node\TeamViewer', r'SOFTWARE\TeamViewer']:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    val, _ = winreg.QueryValueEx(key, 'ClientID')
                    return str(val)
                except Exception:
                    continue
        except Exception:
            pass
    else:
        import re
        try:
            out = subprocess.check_output(['teamviewer', 'info'], text=True, stderr=subprocess.DEVNULL)
            m = re.search(r'TeamViewer ID:\s*(\d+)', out)
            if m:
                return m.group(1)
        except Exception:
            pass
        for conf in ['/opt/teamviewer/config/global.conf',
                     os.path.expanduser('~/.config/teamviewer/global.conf')]:
            try:
                with open(conf) as f:
                    for line in f:
                        m = re.match(r'\s*ClientID\s*=\s*(\d+)', line, re.IGNORECASE)
                        if m:
                            return m.group(1)
            except Exception:
                continue
    return ''

# ── Process check ─────────────────────────────────────────────────────────────

def is_running():
    try:
        exe = getattr(settings, 'appEXEName', '')
        if not exe:
            return ''
        if _IS_WIN:
            for line in os.popen('tasklist').read().splitlines():
                if exe in line:
                    return line
        else:
            result = subprocess.run(['pgrep', '-f', exe], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
    except Exception:
        pass
    return ''

# ── Crash log ─────────────────────────────────────────────────────────────────

crash_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    getattr(settings, 'crashPath', 'crash.log')
)

def read_and_clear_crashes():
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

# ── Send heartbeat ─────────────────────────────────────────────────────────────

def send_pulse(status='', include_crashes=False):
    payload = {
        'tab':         settings.sheetName,
        'exhibit':     settings.exhibitName,
        'host':        host_name,
        'ip':          host_ip,
        'os':          get_os(),
        'memory':      get_memory(),
        'disk':        get_disk(),
        'uptime':      get_uptime(),
        'last_reboot':   get_last_reboot(),
        'teamviewer_id': get_teamviewer_id(),
        'time':          datetime.now().strftime('%m/%d/%Y  %H:%M:%S'),
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
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Pulse OK")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Server error: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"Warning: could not reach server ({e})")

# ── Main loop ─────────────────────────────────────────────────────────────────

CRASH_PULSE_INTERVAL = 5 * 60 * 60  # 5 hours in seconds

print(f"Monitoring {settings.exhibitName} → {pulse_url}")
send_pulse(include_crashes=True)
last_crash_pulse = time.time()

update_counter = 0
while True:
    res = is_running()

    if not res:
        update_counter = 0
        time.sleep(2)
    elif 'Not Responding' in res:
        time.sleep(2)
    else:
        update_counter += 1
        if update_counter == 1:
            send_pulse(status='Ok', include_crashes=True)
            last_crash_pulse = time.time()
        elif time.time() - last_crash_pulse >= CRASH_PULSE_INTERVAL:
            send_pulse(status='Ok', include_crashes=True)
            last_crash_pulse = time.time()
        time.sleep(5)
