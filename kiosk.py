#!/usr/bin/env python
# kiosk.py
#
# Hook module for exhibit-specific handling of serial data, called from
# serial_tcp_client.py alongside forwarding the data over TCP:
#
#     kiosk.send(data)  # If the kiosk has specific logic, put it into kiosk.py
#
# By default this does nothing - serial_tcp_client.py still forwards every
# byte to the TCP socket regardless. Add real logic here only if this
# exhibit needs to react to the serial data itself (e.g. log button
# presses, trigger a local action, filter/transform bytes before they're
# forwarded, etc).
#
# `data` is the raw bytes read from the serial port (may be a single byte,
# since serial_tcp_client.py reads with timeout=1 and no fixed size).


def send(data: bytes) -> None:
    pass
