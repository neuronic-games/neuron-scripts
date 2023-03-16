# Monitor folder for CSV files and send email
# Pyton v2
# Usage: python send_mail_bluk.py

import time
import smtplib, ssl
import csv
import os, fnmatch
import re
import email.utils
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText
from email.encoders import encode_base64
from datetime import datetime
import email_setting
import logging

import ctypes
from ctypes.wintypes import RGB
from ctypes import byref, c_int, windll, wintypes
from os import getenv, getcwd
import keyboard

# Monitors this folder for CSV files containing email address and attachment file
# name. Each file can contain 1 or more rows of data.
folder = email_setting.folder

# Create a secure SSL context (with Python 3)
# context = ssl.create_default_context()

msg_html = email_setting.message
regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
log_file = r'send_mail.log'
logging.basicConfig(filename=os.path.join(folder, log_file), filemode='w', level=logging.INFO)

def time_since(another_time):
    return time.time() - another_time

def setup():
    global start_time
    start_time = time.time()

    print os.path.basename(__file__), "- ver 1"
    print "(c) 2022 Neuronic LLC. All rights reserved."
    print "Logging in", log_file

def open_csv_and_send_mail(file):
    with open(file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            to_addr = row[0].strip()
            file_name = row[1].strip()

        file_path = os.path.join(folder, file_name)
        check = re.search(regex, to_addr)
        if(check != None):
            logging.info("{}: Emailing {} with {}".format(datetime.now(), to_addr, file_name))
            success = send_email_with_attachment(to_addr, file_path)
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

        csv_file.close()
        os.remove(file)
        logging.info("{}: File {} deleted".format(datetime.now(), file))

def send_email(to_addr):
    server = smtplib.SMTP(email_setting.smtp_server, email_setting.port)
    server.ehlo() # Can be omitted
    server.starttls() #context=context) # Secure the connection (with Phyton 3)
    server.ehlo() # Can be omitted
    server.login(email_setting.sender_email, email_setting.password)
    server.sendmail(email_setting.sender_email, to_addr, msg_html)
    server.quit()

def send_email_with_attachment(to_addr, attachment_file):
    msg = MIMEMultipart()
    msg['Subject'] = email_setting.subject
    msg['From'] = email.utils.formataddr([email_setting.sender_name, email_setting.sender_email])
    msg['To'] = to_addr

    part2 = MIMEText(msg_html, 'html')

    part3 = MIMEBase('application', "octet-stream")
    try:
        part3.set_payload(open(attachment_file, "rb").read())
    except:
        logging.info("{}: Error opening {}".format(datetime.now(), attachment_file))
        return False
        
    encode_base64(part3)

    visible_name = "attachment"
    extension = os.path.splitext(attachment_file)[1]
    part3.add_header('Content-Disposition', 'attachment; filename="' + visible_name + extension + '"')

    msg.attach(part2)
    msg.attach(part3)

    try:
        server = smtplib.SMTP(email_setting.smtp_server, email_setting.port)
        server.ehlo() # Can be omitted
        server.starttls() #context=context) # Secure the connection (with Phyton 3)
        server.ehlo() # Can be omitted
        server.login(email_setting.sender_email, email_setting.password)
        server.sendmail(email_setting.sender_email, to_addr, msg.as_string())
        server.quit()
        logging.info("{}: Mail sent to {}".format(datetime.now(), to_addr))
    except Exception as e:
        logging.info("{}: {}".format(datetime.now(), e))
    
    return True
    
try:
    setup()
    
    print "Checking periodically in", folder

    ####################################################################################################
    ## For CMD Console
    # get the handle to the console bar
    consoleBarHandler = ctypes.windll.kernel32.GetConsoleWindow()
    # hide the CMD Console
    windll.user32.ShowWindow(consoleBarHandler, 0)
    ####################################################################################################
    
    while True:
        for filename in fnmatch.filter(os.listdir(folder), '*.csv'):
            logging.info("{}: Processing {}".format(datetime.now(), filename))
            open_csv_and_send_mail(os.path.join(folder, filename))
        
        ########################################################################################################
        # checking for Keybaord press
        if keyboard.is_pressed("left windows") and keyboard.is_pressed("shift") and keyboard.is_pressed("d"):
            # Close CMD Console
            windll.user32.DestroyWindow(consoleBarHandler)
            break
        ########################################################################################################
        time.sleep(0)  # Wait 0 sec  #1 sec

except KeyboardInterrupt:
    print "Exiting gracefully"

except Exception as e:
    # Print any error messages to stdout
    print(e)

finally:
    print "Total execution time (sec): ", time_since(start_time)
    
