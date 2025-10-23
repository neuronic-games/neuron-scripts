# guard.py v1.0
# MUMTAZ (c) Neuronic 2023
# Usage: guard.py

import os, sys, time, subprocess, webbrowser
import logging
from datetime import datetime
import audit_setting
import ctypes
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll, wintypes
from os import getenv, getcwd
import shutil
import keyboard
from multiprocessing import Process

# Calling archive update
import archive_update

APP_EXE_PATH = getattr(audit_setting, 'appEXEPath', r'C:/Program Files/Google/Chrome/Application')
APP_NAME = getattr(audit_setting, 'appName', r'chrome') 
APP_EXE_NAME = getattr(audit_setting, 'appName', r'chrome') 

path = os.path.join(APP_EXE_PATH, APP_NAME, APP_EXE_NAME)
print("Opening " + path)
    
subprocess.Popen(path)
