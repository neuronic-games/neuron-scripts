# Monitor folder for CSV files and send email
# Python v3
# Usage: python send_mail_bluk.py

import time
import csv
import os, fnmatch
import re

from datetime import datetime

import settings_loader  # must run before `import settings` below
import settings
import send_email
import mail_stats
import mail_log
import logging

import ctypes
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll, wintypes
from os import getenv, getcwd
import keyboard

# Monitors this folder for CSV files containing email address and attachment file
# name. Each file can contain 1 or more rows of data.
folder = settings.folder

# Create a secure SSL context (with Python 3)
# context = ssl.create_default_context()

regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
log_file = r'send_mail.log'
logging.basicConfig(filename=os.path.join(folder, log_file), filemode='w', level=logging.INFO)

def time_since(another_time):
    return time.time() - another_time

def setup():
    global start_time
    start_time = time.time()

    print (os.path.basename(__file__), "- ver 1")
    print ("(c) 2022 Neuronic LLC. All rights reserved.")
    print ("Logging in", log_file)

def open_csv_and_send_mail(file):
    with open(file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            to_addr = row[0].strip()
            file_name = row[1].strip()
            file_path = os.path.join(folder, file_name)
            check = re.search(regex, to_addr)
            if(check is not None):
                logging.info("{}: Emailing {} with {}".format(datetime.now(), to_addr, file_name))
                try:
                    send_email.send_email_with_attachment(to_addr, file_path)
                    success = True
                except Exception as e:
                    logging.info("{}: {}".format(datetime.now(), e))
                    success = False
                while success:
                    try:
                        os.remove(file_path)
                        logging.info("{}: File {} deleted".format(datetime.now(), file_path))
                        break
                    except:
                        logging.info("{}: Error deleting {}".format(datetime.now(), file_path))
                        time.sleep(5) # Wait 5 sec before trying to delete again
            else:
                logging.info("{}: Invalid email {}".format(datetime.now(), to_addr))

    # The `with` block has closed the CSV; only delete it once every row
    # has been processed.
    os.remove(file)
    logging.info("{}: File {} deleted".format(datetime.now(), file))

try:
    setup()
    print ("Checking periodically in", folder)

    ####################################################################################################
    ## For CMD Console
    # get the handle to the console bar
    #if(consoleBarHandler != null):
    consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
    # hide the CMD Console
    windll.user32.ShowWindow(consoleBarHandler, 0)
    ####################################################################################################
    
    while True:
        for filename in fnmatch.filter(os.listdir(folder), '*.csv'):
            logging.info("{}: Processing {}".format(datetime.now(), filename))
            open_csv_and_send_mail(os.path.join(folder, filename))

        try:
            mail_stats.send_daily_report_if_due()
        except Exception as e:
            logging.info("{}: Error sending daily report: {}".format(datetime.now(), e))

        ########################################################################################################
        # checking for Keybaord press
        if keyboard.is_pressed("left windows") and keyboard.is_pressed("shift") and keyboard.is_pressed("d"):
            # Close CMD Console
            windll.user32.DestroyWindow(consoleBarHandler)
            break
        ########################################################################################################
        time.sleep(0)  # Wait 0 sec  #1 sec

except KeyboardInterrupt:
    print ("Exiting gracefully")

except Exception as e:
    # Print any error messages to stdout
    print(e)

finally:
    print ("Total execution time (sec): ", time_since(start_time))
    
