import wget
import argparse

wget.download("https://www.dropbox.com/s/gtr5rjb3x589lyl/credentials.json?dl=1")

parser = argparse.ArgumentParser(description='Install Neuron Guard and Neuron Apps.')
parser.add_argument('--archive', nargs='?', help='URL for archive.txt')

args = parser.parse_args()

puts args