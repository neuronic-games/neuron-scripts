# Neuron Installer
# Neuronic (c) 2023 - TAM

import wget
import argparse
import audit_setting
import archive_update
import os

parser = argparse.ArgumentParser(description='Install Neuron Guard and Neuron Apps.')
parser.add_argument('--archive', nargs='?', help='Specify the URL for archive.txt to install a new Neuron App')

args = parser.parse_args()

# Create app folder

folder = os.path.join(audit_setting.appPath, audit_setting.appName)
if not os.path.exists(folder) :
    print ("Creating " + folder)
    os.mkdir(folder)

# Install of Neuron Guard files

if os.path.exists("credentials.json") :
    print ("credentials.json already exists.")
else :
    wget.download("https://www.dropbox.com/s/gtr5rjb3x589lyl/credentials.json?dl=1")
    print ("\n")
    print ("credentials.json installed.")

# Install archive if --archive is used
    
if (args.archive):
    archive = os.path.join(folder, "archive.txt")
    if not os.path.exists(archive):
        print ("Downloading " + archive)
        wget.download(args.archive, folder)
        print ("\n")
        print ("Archive info downloaded.")
    archive_update.checkUpdateStatus()
    exit()

