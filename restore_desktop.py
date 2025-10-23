# (c) Neuronic 2023

import ctypes
import os, sys, time
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll
from os import getenv, getcwd
import shutil
from os import path, getenv, getcwd
import audit_setting

CRASH_LOG = getattr(audit_setting, 'crashPath', r'crash.log')
DESKTOP_COLOR = getattr(audit_setting, 'desktopColor', RGB(65, 57, 121))
RESET_DESKTOP_COLOR = getattr(audit_setting, 'resetDesktopColor', RGB(65, 57, 121))
NEURONIC_LOGO = getattr(audit_setting, 'logoBrand', "logo/neuronic.png")
APP_NAME = audit_setting.appEXEName.split('.exe')[0]

####################################################################################################
### Get Active Wallpapaer
def getWallpaper():
    path = os.path.join(audit_setting.appPath, 'neuron-scripts', 'logo', NEURONIC_LOGO)
    return path

if __name__ == '__main__':
    color = RGB(65, 57, 121) # blue
    taskBarStatus = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    # Reset the background solid color to previous
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(RESET_DESKTOP_COLOR)))
    # Revet back to default set wallpaper
    ctypes.windll.user32.SystemParametersInfoA(20, 0, getWallpaper(), 3)
    # Show the bottom taskbar
    windll.user32.ShowWindow(taskBarStatus, 9)

    # Kill the processes
    # Use if using Python v2+
    taskProcess.terminate()
    keyProcess.terminate()
    # Use if using Python v3+
    #taskProcess.kill()
    #keyProcess.kill()
    # Close the running app
    os.system('taskkill /im ' + '\"' + (APP_NAME + '.exe') + '\" /f')
