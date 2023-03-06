# audit_setting.py v1.2
# MUMTAZ (c) Neuronic 2023

from ctypes.wintypes import RGB

##############################################################################################
# Define google spreadsheet id and default sheet name
sheetID = "1EICxWfCUwpRw5NRcRtIGP24IfunLArfKy3e4PIqG25c"
sheetName = "CMH" # Change accordingly
##############################################################################################
# Unique exhibit name in Google Sheet
exhibitName = "MATCH-MOVES-1" # Change accordingly
##############################################################################################
# This is the root folder of where the Unity EXE will be installed
neuronAppPath = r'C:/Users/admin/Documents/Neuronic/Apps'
neuronAppName = r'My Exhibit App'  # This is the folder name of the app : Change accordingly
##############################################################################################
# App EXE [EXE]
# Use exe name for the respective apps name in non chrome based apps [eg : "hpcm-tv-edit.exe"]
# Use "chrome.exe" for chrome based apps only [eg : "chrome.exe"]
appEXEName = "chrome.exe" # Change accordingly
##############################################################################################
# Change the app path here
# For non chrome based apps [eg : r'C:/Program Files (x86)/hpcm-tv-edit/'] # Path of apps location :::: Change accordingly
# For chrome based apps [eg : r'C:/Program Files/Google/Chrome/Application/'] # Path of Chrome.exe
appEXEPath = r'C:/Program Files/Google/Chrome/Application' 
##############################################################################################
# Fill the URL in case of chrome apps only. Leave blank in case of EXE apps only
appParams = "https://www.neuronicgames.com" # Change accordingly
##############################################################################################
# Crash Log path
crashPath = r'crash.log'
##############################################################################################
# Solid bg color desktop [RGB]
desktopColor = RGB(65, 57, 121) #RGB(65, 57, 121) # 
resetDesktopColor = RGB(65, 57, 121) # Initial desktop bg color
##############################################################################################
# Neuronic Branding Logo
logoBrand = "logo/neuronic.png"
##############################################################################################
# Whether to check for update version of app or not [False in AIR app case]
checkForUpdate = False
##############################################################################################
