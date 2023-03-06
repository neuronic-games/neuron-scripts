# (c) Neuronic 2023

import ctypes
import os, sys, time
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll
from os import getenv, getcwd
import shutil
from os import path, getenv, getcwd
import audit_setting

NEURONIC_LOGO = r'neuronic.png'
CRASH_LOG = r'crash.log'
DESKTOP_COLOR = RGB(0, 0, 0)

####################################################################################################
### Get Active Wallpapaer
def getWallpaper():
    path = os.path.join(audit_setting.appPath, 'neuron-scripts', 'logo', NEURONIC_LOGO)
    return path

if __name__ == '__main__':
    color = RGB(65, 57, 121) # blue
    taskBarStatus = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    #changeSystemColor(color)
    color = DESKTOP_COLOR
    # Reset the background solid color to previous
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(color)))
    # Revet back to default set wallpaper
    ctypes.windll.user32.SystemParametersInfoA(20, 0, getWallpaper(), 3)
    # Show the bottom taskbar
    windll.user32.ShowWindow(taskBarStatus, 9)