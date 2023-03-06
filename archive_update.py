# archive_update.py v1.2
# TAM (c) Neuronic 2021

# USAGE
# Run this script in the folder where the archive will be extracted. If the
# archive already exist, version.txt file must also exist in this folder.
# The file archive.txt that defines the archive must exist in the same folder.

# INSTALLATION
# pip install wget
# pip install zipfile36

import os, time
import wget
from zipfile import ZipFile
import audit_setting
from os.path import exists
import shutil
from os import getenv, getcwd

extract_dir = "."
archive_info_file = "archive.txt"
version_cur_file = "version.txt"
version_new_file = "version.new.txt"
current_version = "0"
checkOnce = False
# Download Status
downloadCompleted = False
checkForUpdate = False

#############################################################
# Method to compare two versions.
# Return 1 if v2 is smaller,
#       -1 if v1 is smaller,
#        0 if equal
def versionCompare(v1, v2):
     
    # This will split both the versions by '.'
    arr1 = v1.split(".")
    arr2 = v2.split(".")
    n = len(arr1)
    m = len(arr2)
     
    # converts to integer from string
    arr1 = [int(i) for i in arr1]
    arr2 = [int(i) for i in arr2]
  
    # compares which list is bigger and fills
    # smaller list with zero (for unequal delimeters)
    if n>m:
      for i in range(m, n):
         arr2.append(0)
    elif m>n:
      for i in range(n, m):
         arr1.append(0)
     
    # returns 1 if version 1 is bigger and -1 if
    # version 2 is bigger and 0 if equal
    for i in range(len(arr1)):
      if arr1[i]>arr2[i]:
         return 1
      elif arr2[i]>arr1[i]:
         return -1
    return 0
#############################################################
def checkUpdateStatus(checkForUpdate):
    extract_dir = audit_setting.archivePath
    archive_info_file = audit_setting.archivePath + "/archive.txt"
    version_cur_file = audit_setting.archivePath + "/version.txt"
    version_new_file = "" #"C:/Users/Legion/Documents/Neuronic/version.new.txt"
    current_version = "0"
    newPath = os.getcwd()

    # Download Status
    downloadCompleted = False
    if (audit_setting.checkForUpdate or checkForUpdate):  
        # Read the current version from version.txt
        archive_file_exists = exists(archive_info_file)
        if (not archive_file_exists):
            print (archive_info_file, "does not exist in this folder.")
            downloadCompleted = False
        else:
            print ("Reading " + archive_info_file)
            # Read version.txt
            f = open(archive_info_file, 'r')
            archive = f.readline().strip()
            version_url = f.readline().strip()
            archive_url = f.readline().strip()
            f.close()

            # Cleanup of update.txt if necessary
            if os.path.exists(archive_info_file):
                os.remove(archive_info_file)

            print ("Checking latest version of", archive)
            archive_info_file_new = wget.download(version_url, extract_dir)

            #print

            f = open(archive_info_file_new, 'r')
            archive = f.readline().strip()
            version_url = f.readline().strip()
            archive_url = f.readline().strip()
            archive_version = f.readline().strip()
            f.close()

            # If version.txt exists, use this as the version number
            if os.path.exists(version_cur_file):
                f = open(version_cur_file, 'r')
                current_version = f.readline().strip()
                f.close()
                
            print ("Archive:", archive_url)
            print ("Latest:", archive_version)
            print ("Current:", current_version)

            # remove downloaded archive_info_file 
            os.remove(archive_info_file)

            # Download newer archive
            if versionCompare(archive_version, current_version) == 1:
                print ("Downloading version", archive_version, "from", archive_url)
                archive_filename = wget.download(archive_url, extract_dir)
                #print

                print ("Extracting", archive_filename)
                zf = ZipFile(archive_filename, 'r')
                zf.extractall(extract_dir)
                zf.close()

                # Remove the archive
                os.remove(archive_filename)

                # move file
                path = os.path.join(newPath, archive_info_file_new)
                shutil.move(path, archive_info_file)
                
                # Remember the downloaded version
                f = open(version_cur_file, 'w')
                f.write(archive_version)
                f.close()
                downloadCompleted = True
                
            else:
                print ("No new archive")
                path = os.path.join(newPath, archive_info_file_new)
                if os.path.exists(path):
                    os.remove(path)
                downloadCompleted = True
    return downloadCompleted
