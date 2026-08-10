# restore_desktop.py v2.0
# Restore the desktop and kill the monitored app. Cross-platform.
# Neuronic 2025

import os, sys, subprocess
import settings

_IS_WIN = sys.platform == 'win32'

APP_EXE_NAME = getattr(settings, 'appEXEName', '')
LOGO_BRAND   = getattr(settings, 'logoBrand',  'neuronic.png')

_script_dir = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    # Kill the monitored app
    if APP_EXE_NAME:
        if _IS_WIN:
            os.system(f'taskkill /im "{APP_EXE_NAME}" /f')
        else:
            subprocess.run(['pkill', '-f', APP_EXE_NAME], capture_output=True)

    # Restore Windows desktop
    if _IS_WIN:
        import ctypes
        from ctypes import byref, c_int, windll
        from ctypes.wintypes import RGB

        RESET_COLOR = getattr(settings, 'resetDesktopColor', RGB(0, 0, 0))
        logo_path   = os.path.join(_script_dir, 'logo', LOGO_BRAND)

        task_bar = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
        ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(RESET_COLOR)))
        ctypes.windll.user32.SystemParametersInfoW(20, 0, logo_path, 3)
        windll.user32.ShowWindow(task_bar, 9)

    # Kill all Python processes (guard, report_status, etc.)
    if _IS_WIN:
        os.system('taskkill /im python.exe /f')
    else:
        subprocess.run(['pkill', '-f', 'python'], capture_output=True)

    print('Desktop restored.')
