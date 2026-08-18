#!/usr/bin/env python
#
# (c) Neuronic LLC 2019

import sys
import socket
import serial
import time
import datetime
import kiosk

HOST = 'localhost'
PORT = 55555              # The same port as used by the server
BAUD = 9600

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Direct communication from serial and TCP socket.")

    parser.add_argument('SERIALPORT')

    parser.add_argument(
        '-p', '--localport',
        type=int,
        help='local TCP port, default: %(default)s',
        metavar='TCPPORT',
        default=PORT)

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='print data received from serial port and sent to tcp socket',
        default=False)

    args = parser.parse_args()
    
try:

    tcp = None
    arduino = None

    while True:
        
        try:
    
            if not tcp:
                tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp.connect((HOST, args.localport))
                sys.stderr.write('{} Connect to tcp {}\n'.format(datetime.datetime.now(), args.localport))

            if not arduino:
                arduino = serial.Serial(
                  port = args.SERIALPORT,
                  baudrate = BAUD,
                  parity = serial.PARITY_NONE,
                  stopbits = serial.STOPBITS_ONE,
                  bytesize = serial.EIGHTBITS,
                  timeout = 1
                )
                sys.stderr.write('{} Connect to serial {}\n'.format(datetime.datetime.now(), args.SERIALPORT))
            
            # Read from arduino serial
            data = arduino.read()

            # Write to tcp socket
            if data:
                kiosk.send(data)  # If the kiosk has specific logic, put it into kiosk.py
                tcp.send(data)

                if args.verbose:
                    sys.stderr.write(data.decode('utf-8', errors='replace'))

        except serial.serialutil.SerialException as e:
            sys.stderr.write('{} ARDUINO ERROR: {}\n'.format(datetime.datetime.now(), e))

            if arduino:
                arduino.close()
            arduino = None

            time.sleep(5)

        except ConnectionRefusedError as e:
            sys.stderr.write('{} TCP ERROR: No one is listening on {}:{} - is the exhibit app running?\n'.format(
                datetime.datetime.now(), HOST, args.localport))

            if tcp:
                tcp.close()
            tcp = None

            time.sleep(5)

        except socket.error as e:
            sys.stderr.write('{} TCP ERROR: {}\n'.format(datetime.datetime.now(), e))

            if tcp:
                tcp.close()
            tcp = None

            time.sleep(5)
            
except KeyboardInterrupt:
    pass

if tcp:
    tcp.close()
if arduino:
    arduino.close()
    
sys.stderr.write('\n--- exit ---\n')
