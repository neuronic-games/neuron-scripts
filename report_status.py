# report_status.py v1.0
# MUMTAZ (c) Neuronic 2023

import os, sys, time, subprocess, webbrowser
import gspread
from datetime import datetime
import logging
import audit_setting
import socket

import ctypes
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll, wintypes
from os import getenv, getcwd
import keyboard
################################################################################################
############# Make connection to the google sheet #############
# Credentials [Keys etc]
credPath = ""
credFileName = credPath + "credentials.json"
mServiceAccount = gspread.service_account(filename=credFileName)
################################################################################################
# Google sheet Id
mGoogleSheetId = audit_setting.sheetID # FOR TESTING
################################################################################################
# Connect the sheet based on sheet id
mGoogleSheet = mServiceAccount.open_by_key(mGoogleSheetId)
################################################################################################
############# Define Sheet name to be edited #############
if(audit_setting.sheetName == ""):
    sheetName = mGoogleSheet.worksheets()[0].title
else:
    sheetName = audit_setting.sheetName
################################################################################################
# Acees google sheet from the mentioned sheet name
mSelectedWorkSheet = mGoogleSheet.worksheet(sheetName)
################################################################################################
############# Define the installed path for the app #############
# FOR EXE/CHROME
appDefaultPath = audit_setting.appEXEPath
################################################################################################
# crash log For updating the google audit sheet
crash_file = audit_setting.crashPath
################################################################################################
## For CMD Console
# get the handle to the console bar
consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
# hide the CMD Console
windll.user32.ShowWindow(consoleBarHandler, 0)
####################################################################################################
# Message
print ("Updating google sheet periodically...")
################################################################################################
# Update sheet delay
updateCounter = 0
#maxIteration = 50
################################################################################################
# Assign google sheet row and col for that machine name
cellNum = mSelectedWorkSheet.find(audit_setting.exhibitName)
# Get machine postion from the google sheet
machinIndex = cellNum.row
################################################################################################
### Refresh Counter ###
isRefreshed = False
totalStr = ''
################################################################################################
#### Store IP and Host of a machine and update to google sheet
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
mSelectedWorkSheet.update(('B' + str(machinIndex)), host_name)
mSelectedWorkSheet.update(('C' + str(machinIndex)), host_ip)
################################################################################################
# Open the crash log file and update to google sheet and clear the log file
# update google sheet
with open(crash_file, 'r') as cLog:
    total_crash = len(cLog.readlines())
    # update google sheet
    mSelectedWorkSheet.update(('F' + str(machinIndex)), total_crash)
# Write Crash Report
with open(crash_file, 'r') as cLog:
    totalStr = ''
    for line in cLog:
        d = line.split(": App Restarted")[0].split(".")[0].split(":", 2)[2].split(' ')[1]
        totalStr += d + ", "
# update google sheet
## Remove last , from the string
totalStr = totalStr[:len(totalStr)-2]
mSelectedWorkSheet.update(('G' + str(machinIndex)), totalStr)
with open(crash_file, 'w') as cLog:
    print('Updated the crash report to google sheet for the day!!!')
################################################################################################
############# Getting the list of all running process from the task manager #############
# Filter the app passed as param 'name'
try:
    def getTasks(name):
        response = []
        response = os.popen('tasklist').read().strip().split('\n')
        #print(response[0].split('Mem Usage'))
        # print ('# of tasks is %s' % (len(response)))
        for i in range(len(response)):
            s = response[i]
            #print (name + " ---- ", response[i])
            if name in response[i]:
                # print ('%s in response[i]' %(name))
                return response[i]
        return []
    if __name__ == '__main__':
        '''
        Timer to call the func (every 1 sec)
        '''
        while True:
            appName = audit_setting.appEXEName.split('.exe')[0]
            notResponding = 'Not Responding'
            # res = getTasks(imgName)
            res = getTasks((appName + '.exe'))
            #print(res)
            if not res:
                ####################################################################
                updateCounter = 0
                ####################################################################
                isChromeApp = appDefaultPath.find('Chrome')
                if(isChromeApp != -1):
                    appURL = audit_setting.appParams
                    #######################################################################
                    now = datetime.now()
                    # convert to string
                    time_str = now.strftime("%m/%d/%Y  %H:%M:%S")
                    #######################################################################
                else:
                    #######################################################################
                    now = datetime.now()
                    # convert to string
                    time_str = now.strftime("%m/%d/%Y  %H:%M:%S")
                    #######################################################################
                    time.sleep(1)
            elif 'Not Responding' in res:
                #######################################################################
                #mSelectedWorkSheet.update(('D' + str(machinIndex)), "App Not Responding")
                #######################################################################
                now = datetime.now()
                # convert to string
                time_str = now.strftime("%m/%d/%Y  %H:%M:%S")
                #######################################################################
                time.sleep(1)
            else:
                if(machinIndex != -1):
                    # terminating process
                    #print('%s - Running ' % (appName))
                    updateCounter = updateCounter+1
                    if(updateCounter == 1):
                        ############# Update Cell value #############
                        now = datetime.now()
                        ####################################################
                        # convert to string
                        date_time_str = now.strftime("%m/%d/%Y")
                        time_str = now.strftime("%m/%d/%Y  %H:%M:%S")
                        ####################################################
                        # Update Date row to the current Audit
                        ####################################################
                        mSelectedWorkSheet.update(('D' + str(machinIndex)), "Ok")
                        mSelectedWorkSheet.update(('E' + str(machinIndex)), time_str)
                        print('Google Sheet Updated')
                        ####################################################
                    else:
                        # check for status date column to be updated based on day change
                        now = datetime.now()
                        time_str = now.strftime("%H:%M:%S")
                        if (time_str == '00:00:00'):
                            ####################################################
                            ## Update Host Name and Host IP to google sheet
                            mSelectedWorkSheet.update(('B' + str(machinIndex)), host_name)
                            mSelectedWorkSheet.update(('C' + str(machinIndex)), host_ip)
                            ############# Update Cell value #############
                            ####################################################
                            # convert to string
                            date_time_str = now.strftime("%m/%d/%Y")
                            time_str = now.strftime("%m/%d/%Y  %H:%M:%S")
                            ####################################################
                            # Update Date row to the current Audit
                            ####################################################
                            mSelectedWorkSheet.update(('D' + str(machinIndex)), "Ok")
                            mSelectedWorkSheet.update(('E' + str(machinIndex)), time_str)
                            ####################################################
                            # Open the crash log file and update to google sheet and clear the log file
                            # update google sheet
                            with open(crash_file, 'r') as cLog:
                                total_crash = len(cLog.readlines())
                                # update google sheet
                                mSelectedWorkSheet.update(('F' + str(machinIndex)), total_crash)
                            # Write Crash Report
                            with open(crash_file, 'r') as cLog:
                                totalStr = ''
                                for line in cLog:
                                    d = line.split(": App Restarted")[0].split(".")[0].split(":", 2)[2].split(' ')[1]
                                    totalStr += d + ", "
                            # update google sheet
                            ## Remove last , from the string
                            totalStr = totalStr[:len(totalStr)-2]
                            mSelectedWorkSheet.update(('G' + str(machinIndex)), totalStr)
                            with open(crash_file, 'w') as cLog:
                                print('Updated the crash report to google sheet for the day!!!')
                #else:
                ########################################################################################################
                # checking for Keybaord press
                if keyboard.is_pressed("left windows") and keyboard.is_pressed("shift") and keyboard.is_pressed("d"):
                    # Close CMD Console
                    windll.user32.DestroyWindow(consoleBarHandler)
                    break
                ########################################################################################################
                time.sleep(0)
except KeyboardInterrupt:
    print("Google sheet update script stopped")