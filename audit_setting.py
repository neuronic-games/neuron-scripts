# audit_setting.py v1.2
# MUMTAZ (c) Neuronic 2023

from ctypes.wintypes import RGB

##############################################################################################
# Define google spreadsheet id and default sheet name for status reports
sheetID = "1EICxWfCUwpRw5NRcRtIGP24IfunLArfKy3e4PIqG25c"
sheetName = "???" # e.g. CMH
##############################################################################################
# Unique exhibit name in Google Sheet
exhibitName = "???" # e.g. SKELETAL-POP-1
##############################################################################################
# This is the root folder of where the Unity EXE will be installed
appPath = r'C:/Users/admin/Documents/Neuronic/Apps'
appName = '???'  # e.g. Skeletal Pop
##############################################################################################
# Use exe name for the respective apps name in non chrome based apps [eg : "hpcm-tv-edit.exe"]
# Use "chrome.exe" for chrome based apps only [eg : "chrome.exe"]
appEXEPath = r'C:/Program Files/Google/Chrome/Application' 
appEXEName = '???' # e.g. skeletal-pop.exe
##############################################################################################
# Change the app path here
# For non chrome based apps [eg : r'C:/Program Files (x86)/hpcm-tv-edit/'] # Path of apps location :::: Change accordingly
# For chrome based apps [eg : r'C:/Program Files/Google/Chrome/Application/'] # Path of Chrome.exe
##############################################################################################
# Fill the URL in case of chrome apps only. Leave blank in case of EXE apps only
appParams = "???" # e.g. https://www.neuronicgames.com
##############################################################################################
# Neuronic Branding Logo
logoBrand = "logo/neuronic.png"
##############################################################################################
# Whether to check for update version of app or not [False in AIR app case]
checkForUpdate = False
##############################################################################################
