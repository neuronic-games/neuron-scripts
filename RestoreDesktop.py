#from ctypes import windll
import ctypes
import os, sys, time
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll
from os import getenv, getcwd
import shutil
from os import path, getenv, getcwd
import audit_setting

target = 'background\\'
####################################################################################################
### Get Active Wallpapaer
def getWallpaper():
    currentWallpaper = os.listdir(target)
    cwd = os.getcwd()
    imgName = target + currentWallpaper[0]
    path = os.path.join(cwd, imgName)
    return path
if __name__ == '__main__':
    color = RGB(65, 57, 121) # blue
    taskBarStatus = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    #changeSystemColor(color)
    color = audit_setting.resetDesktopColor
    # Reset the background solid color to previous
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(color)))
    # Revet back to default set wallpaper
    ctypes.windll.user32.SystemParametersInfoA(20, 0, getWallpaper(), 3)
    # Show the bottom taskbar
    windll.user32.ShowWindow(taskBarStatus, 9)