import wget
import argparse
import audit_setting
import archive_update
import os

parser = argparse.ArgumentParser(description='Install Neuron Guard and Neuron Apps.')
parser.add_argument('--archive', nargs='?', help='URL for archive.txt')

args = parser.parse_args()

if (args.archive):
    folder = audit_setting.archivePath
    if not os.path.exists(folder) :
        print ("Creating " + folder)
        os.mkdir(folder)
    archive = folder + "/archive.txt"
    if not os.path.exists(archive):
        print ("Downloading " + archive)
        wget.download(args.archive, folder)
        print ("\n")
        archive_update.checkUpdateStatus(True)
        print ("Archive installed.")
    exit()

# Basic install of Neuron Guard
    
wget.download("https://www.dropbox.com/s/gtr5rjb3x589lyl/credentials.json?dl=1")
print ("\n")
print ("Neuron Guard installed.")