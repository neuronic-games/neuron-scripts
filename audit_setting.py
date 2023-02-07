# audit_setting.py v1.0
# MUMTAZ (c) Neuronic 2023

from ctypes.wintypes import RGB
##############################################################################################
########################### PARAMETERS #######################
# Define google spreadsheet id and default sheet name
sheetID = "1c659GuOcNqhqf911uVq8Na-IUd-miBDY11POF17K2SY" #"1EICxWfCUwpRw5NRcRtIGP24IfunLArfKy3e4PIqG25c"
sheetName = "audit_new" #"HPCM"
##############################################################################################
# App EXE [EXE]
# Use exe name for the respective apps name in non chrome based apps [eg : "hpcm-tv-edit.exe"]
# Use "chrome.exe" for chrome based apps only [eg : "chrome.exe"]
appEXEName = "PowerGrid.exe" # Change accordingly
##############################################################################################
# Change the app path here
# For non chrome based apps [eg : r'C:/Program Files (x86)/hpcm-tv-edit/'] # Path of apps location :::: Change accordingly
# For chrome based apps [eg : r'C:/Program Files/Google/Chrome/Application/'] # Path of Chrome.exe
appEXEPath = r'C:/Program Files (x86)/PowerGrid/' 
##############################################################################################
# Fill the URL in case of chrome apps only. Leave blank in case of EXE apps only
appPath = "http://localhost/mars2" # App Path : Change accordingly
##############################################################################################
# Machine Title [Exhibit] from google sheet
exhibitName = "TV-EDIT" # Change accordingly
##############################################################################################
# Crash Log path
crashPath = r'crash.log'
##############################################################################################
# Solid bg color desktop [RGB]
desktopColor = RGB(142, 140, 216) #RGB(65, 57, 121) # 
resetDesktopColor = RGB(142, 140, 216) # Initial desktop bg color
##############################################################################################
# Neuronic Branding Logo
logoBrand = "logo/msmm_logo.png"
##############################################################################################
# Whether to check for update version of app or not [False in AIR app case]
checkForUpdate = False
##############################################################################################