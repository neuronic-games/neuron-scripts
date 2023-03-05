import wget
import argparse

parser = argparse.ArgumentParser(description='Install Neuron Guard and Neuron Apps.')
parser.add_argument('--archive', nargs='?', help='URL for archive.txt')

args = parser.parse_args()

if (args.archive):
    wget.download(args.archive)
    exit

// Basic install of Neuron Guard
    
wget.download("https://www.dropbox.com/s/gtr5rjb3x589lyl/credentials.json?dl=1")
