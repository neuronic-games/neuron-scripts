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

413a7b
crash_path = getattr(audit_setting, 'crashPath', r'crash.log')
desktop_color = getattr(audit_setting, 'desktopColor', RGB(0, 0, 0))  # purple RGB(65, 58, 123)
reset_desktop_color = getattr(audit_setting, 'resetDesktopColor', RGB(0, 0, 0))
logo_brand = getattr(audit_setting, 'logoBrand', "neuronic.png")

# Calling archive update
import archive_update
####################################################################################################
def initApp():
    ####################################################################################################
    # Var to check for auto update whenever app gets started
    initApp.isStarted = False
    ####################################################################################################
    ## Hide Task Bar
    # get the handle to the taskbar
    initApp.taskBarStatus = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    # hide the bottom taskbar
    windll.user32.ShowWindow(initApp.taskBarStatus, 0)
    ####################################################################################################
    ## For CMD Console
    # get the handle to the console bar
    initApp.consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
    # hide the CMD Console
    windll.user32.ShowWindow(initApp.consoleBarHandler, 0)
    ####################################################################################################
    # Message
    print ("Checking status periodically...")
    # Set the background solid color
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(desktop_color)))
    # Hide the active dektop background image
    script_path = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(script_path, 'logo', logo_brand)
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
    
####################################################################################################
# Getting the list of all running process from the task manager
# Filter the app passed as param 'name'
####################################################################################################
# Define the installed path for the app
# FOR EXE/CHROME
appDefaultPath = audit_setting.appEXEPath
####################################################################################################
# crash log For writing the stats : add crash.log in the same folder
folder = ''
logging.basicConfig(filename=os.path.join(folder, crash_path), filemode='w', level=logging.INFO)
### Copy Active file to background folder
# Providing the folder path
target = 'background\\'
####################################################################################################
### Get Active Wallpapaer
def getWallpaper():
    currentWallpaper = os.listdir(target)
    cwd = os.getcwd()
    imgName = target + currentWallpaper[0]
    path = os.path.join(cwd, imgName)
    return path
####################################################################################################
try:
    ########################################################################################################
    def getTasks(name):
        response = []
        response = os.popen('tasklist /v').read().strip().split('\n')
        #print(response[0].split('Mem Usage'))
        # print ('# of tasks is %s' % (len(response)))
        for i in range(len(response)):
            s = response[i]
            # print (name + " ---- ", response[i])
            if name in response[i]:
                #print ('%s in response[i]' %(name))
                return response[i]
        return []
    ########################################################################################################   
    def getTaskProcess():
        '''
        Timer to call the func (every 5 sec)
        '''
        while True:
            appName = audit_setting.appEXEName.split('.exe')[0]
            notResponding = 'Not Responding'
            # res = getTasks(imgName)
            res = getTasks((appName + '.exe'))
            #print(res, " >>> ")
            if not res:
                print('%s - Started' % (appName))
                # Opening the app in maximized mode
                SW_MAXIMIZE = 3
                info = subprocess.STARTUPINFO()
                info.dwFlags = subprocess.STARTF_USESHOWWINDOW
                info.wShowWindow = SW_MAXIMIZE
                ################################################################################################
                isChromeApp = appDefaultPath.find('Chrome')
                if(isChromeApp != -1):
                    appURL = audit_setting.appPath
                    chromeCMD = r'start chrome {}'.format(appURL) + " --start-fullscreen --kiosk --disable-pinch --overscroll-history-navigation=0"
                    subprocess.Popen(chromeCMD, shell = True)
                else:
                    subprocess.Popen((appDefaultPath + appName + '.exe'))
                logging.info("{}: App Restarted".format(datetime.now()))
            elif notResponding in res:
                print('%s - Not responding' % (appName + '.exe'))
                os.system('taskkill /im ' + '\"' + (appName + '.exe') + '\" /f')
            #else:
               
            # Repeat Timer delay
            #print(len(res), " ---- ")
            if len(res) == 0:
                time.sleep(25)
            else:
                time.sleep(5)
    ########################################################################################################
    def startAllProcess():
        # Get App Name
        appName = audit_setting.appEXEName.split('.exe')[0]

        # Check whether to look for update version of app or not
        if audit_setting.checkForUpdate == True:
            # Checking update status
            _updateStatus = archive_update.checkUpdateStatus()
            while True:
                if _updateStatus == True:
                    #print("App Started : ")
                    _updateStatus = False
                    #break
                    # Calling Process
                    # Task Process
                    taskProcess = Process(target=getTaskProcess)
                    taskProcess.start()
                    
                    # Key Process
                    keyProcess = Process(target=checkKeyPress)
                    keyProcess.start()

                    break
                else:
                    _status = checkKeyPress()
                    if _status == True:
                        # Reset the background solid color to previous
                        ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(reset_desktop_color)))
                        # Revet back to default set wallpaper
                        ctypes.windll.user32.SystemParametersInfoW(20, 0, getWallpaper(), 3)
                        # Show the bottom taskbar
                        windll.user32.ShowWindow(initApp.taskBarStatus, 9)
                        # Close CMD Console
                        windll.user32.DestroyWindow(initApp.consoleBarHandler)
                        # Kill the processes
                        # Use if using Python v2+
                        taskProcess.terminate()
                        keyProcess.terminate()
                        # Use if using Python v3+
                        #taskProcess.kill()
                        #keyProcess.kill()
                        # Close the running app
                        os.system('taskkill /im ' + '\"' + (appName + '.exe') + '\" /f')
                        break
        else:
            targetProcess = getTaskProcess()
            taskProcess = Process(target=targetProcess)
            taskProcess.start()
            print("Starting " + targetProcess)
            
            # Key Process
            keyProcess = Process(target=checkKeyPress)
            keyProcess.start()


            # Reading Status of Keyboard Press
            while True:
                _status = checkKeyPress()
                #print(_status, " CSTATUS")
                if _status == True:
                    # Reset the background solid color to previous
                    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(reset_desktop_color)))
                    # Revet back to default set wallpaper
                    ctypes.windll.user32.SystemParametersInfoW(20, 0, getWallpaper(), 3)
                    # Show the bottom taskbar
                    windll.user32.ShowWindow(initApp.taskBarStatus, 9)
                    # Close CMD Console
                    windll.user32.DestroyWindow(initApp.consoleBarHandler)
                    # Kill the processes
                    # Use if using Python v2+
                    taskProcess.terminate()
                    keyProcess.terminate()
                    # Use if using Python v3+
                    #taskProcess.kill()
                    #keyProcess.kill()
                    # Close the running app
                    os.system('taskkill /im ' + '\"' + (appName + '.exe') + '\" /f')
                    break

    ########################################################################################################
    def checkKeyPress():
        _KeyMatched = False
        if keyboard.is_pressed("f10"):
            _KeyMatched = True
        
        return _KeyMatched
    ########################################################################################################
    if __name__ == '__main__':
        ## Init Vars
        initApp()
        ## Start Process
        startAllProcess()
    ########################################################################################################   
except KeyboardInterrupt:
    # Reset the background solid color to previous
    ctypes.windll.user32.SetSysColors(1, byref(c_int(1)), byref(c_int(reset_desktop_color)))
    # Revet back to default set wallpaper
    ctypes.windll.user32.SystemParametersInfoW(20, 0, getWallpaper(), 3)
    # Show the bottom taskbar
    windll.user32.ShowWindow(initApp.taskBarStatus, 9)
    # Close CMD Console
    windll.user32.DestroyWindow(initApp.consoleBarHandler)
    # Kill the processes
    # Use if using Python v2+
    #taskProcess.terminate()
    #keyProcess.terminate()
    # Use if using Python v3+
    taskProcess.kill()
    keyProcess.kill()
    # Close the running app
    os.system('taskkill /im ' + '\"' + (appName + '.exe') + '\" /f')
    print("Audit script stopped")
