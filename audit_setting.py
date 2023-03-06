# audit_setting.py v1.3
# MUMTAZ (c) Neuronic 2023

from ctypes.wintypes import RGB

# Define google spreadsheet id and default sheet name for status reports
sheetID = "1EICxWfCUwpRw5NRcRtIGP24IfunLArfKy3e4PIqG25c"
sheetName = "???" # e.g. CMH

# Unique exhibit name in Google Sheet
exhibitName = "???" # e.g. SKELETAL-POP-1

# Folder for apps and app data
appPath = r'C:/Users/admin/Documents/Neuronic/Apps'
appName = '???'  # e.g. Skeletal Pop

# Folder for EXE file and its name
appEXEPath = r'C:/Program Files/Google/Chrome/Application' # e.g. r'C:/Users/admin/Documents/Neuronic/Apps/Skeletal Pop/Skeletal Pop Win'
appEXEName = 'chrome.exe' # e.g. skeletal-pop.exe

# Parameters for the EXE or URL for web browser
appParams = "https://www.neuronicgames.com"

# Client logo to be displayed on the desktop
logoName = "neuronic.png"

# Check for latest archive defined in archive.txt (False for AIR app)
checkForUpdate = False
