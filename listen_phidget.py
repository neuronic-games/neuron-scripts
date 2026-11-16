#!/usr/bin/env python
# listen_phidget.py
# Neuronic 2026
#
# Presses keys when a Phidget's digital inputs change - e.g. a big button
# wired to a Phidget InterfaceKit holds SPACE in the app while it's pressed.
# Configured in settings_phidget.py (see settings_phidget.py.sample).
#
# guard.py starts this automatically when settings_phidget.py exists, with
# no window (so it can't take the keyboard focus from the app), restarts it
# if it stops, and stops it on Ctrl+Shift+S. Its output goes to
# listen_phidget.log. To test by hand: py -3 listen_phidget.py
#
# Unlike a plain openWaitForAttachment(), this never gives up when the
# Phidget isn't there yet (still starting after boot, unplugged, open in
# the Phidget Control Panel): the Phidget library keeps looking in the
# background and the input starts working as soon as it attaches.

import importlib.util
import os
import sys
import time
import logging

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', stream=sys.stdout)
log = logging.getLogger('listen_phidget')
for h in logging.getLogger().handlers:
    try:
        h.stream.reconfigure(line_buffering=True)
    except Exception:
        pass


def load_settings():
    path = os.path.join(_SCRIPT_DIR, 'settings_phidget.py')
    if not os.path.isfile(path):
        log.error('settings_phidget.py not found in %s - nothing to do. '
                  'Copy settings_phidget.py.sample to settings_phidget.py.', _SCRIPT_DIR)
        sys.exit(2)
    spec = importlib.util.spec_from_file_location('settings_phidget', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entries = list(getattr(module, 'phidgetKeys', []) or [])
    good = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or not e.get('key'):
            log.error('phidgetKeys entry %d has no "key" - skipped: %r', i, e)
            continue
        good.append(e)
    if not good:
        log.error('phidgetKeys in settings_phidget.py is empty - nothing to do.')
        sys.exit(2)
    return good


def describe(e):
    parts = []
    if e.get('serial') is not None:
        parts.append(f"board {e['serial']}")
    if e.get('hubPort') is not None:
        parts.append(f"hub port {e['hubPort']}")
    if e.get('channel') is not None:
        parts.append(f"input {e['channel']}")
    where = ', '.join(parts) or 'first digital input'
    return f"{where} -> {e['key']} ({e.get('mode', 'hold')})"


class Button:
    """One phidgetKeys entry: a DigitalInput channel mapped to a key."""

    def __init__(self, entry, DigitalInput, keyboard):
        self.e = entry
        self.key = entry['key']
        self.mode = str(entry.get('mode', 'hold')).lower()
        self.invert = bool(entry.get('invert', False))
        self.keyboard = keyboard
        self.held = False
        self.label = describe(entry)
        self.attached = False

        ch = DigitalInput()
        if entry.get('serial') is not None:
            ch.setDeviceSerialNumber(int(entry['serial']))
        if entry.get('hubPort') is not None:
            ch.setHubPort(int(entry['hubPort']))
        if entry.get('hubPortDevice'):
            ch.setIsHubPortDevice(True)
        if entry.get('channel') is not None:
            ch.setChannel(int(entry['channel']))
        ch.setOnAttachHandler(self.on_attach)
        ch.setOnDetachHandler(self.on_detach)
        ch.setOnErrorHandler(self.on_error)
        ch.setOnStateChangeHandler(self.on_state)
        self.ch = ch

    def open(self):
        # open() (not openWaitForAttachment) never times out: the library
        # keeps trying in the background and calls on_attach when it can.
        self.ch.open()

    def on_attach(self, _ch):
        self.attached = True
        try:
            info = f"{self.ch.getDeviceName()} (serial {self.ch.getDeviceSerialNumber()}, input {self.ch.getChannel()})"
        except Exception:
            info = 'Phidget'
        log.info('Attached: %s - %s', info, self.label)

    def on_detach(self, _ch):
        self.attached = False
        self.release()
        log.warning('Detached: %s - unplugged? Waiting for it to come back.', self.label)

    def on_error(self, _ch, code, description):
        log.warning('Phidget error on %s: %s (%s)', self.label, description, code)

    def on_state(self, _ch, state):
        on = bool(state) != self.invert
        try:
            if self.mode == 'tap':
                if on:
                    self.keyboard.send(self.key)
                    log.info('%s pressed -> %s', self.label.split(' -> ')[0], self.key)
            elif on and not self.held:
                self.keyboard.press(self.key)
                self.held = True
                log.info('%s pressed -> holding %s', self.label.split(' -> ')[0], self.key)
            elif not on and self.held:
                self.release()
        except Exception as e:
            log.error('Could not press %s: %s', self.key, e)

    def release(self):
        if self.held:
            try:
                self.keyboard.release(self.key)
            except Exception:
                pass
            self.held = False

    def close(self):
        self.release()
        try:
            self.ch.close()
        except Exception:
            pass


def main():
    log.info('=== listen_phidget.py starting ===')
    entries = load_settings()
    try:
        from Phidget22.Devices.DigitalInput import DigitalInput
    except ImportError:
        log.error('The Phidget22 Python library is missing. Install it with: '
                  'py -3 -m pip install phidget22  (and the Phidget22 software '
                  'for Windows from phidgets.com).')
        sys.exit(2)
    import keyboard

    buttons = [Button(e, DigitalInput, keyboard) for e in entries]
    for b in buttons:
        log.info('Listening: %s', b.label)
        b.open()

    started = time.monotonic()
    warned_at = 0.0
    try:
        while True:
            time.sleep(1)
            waiting = [b for b in buttons if not b.attached]
            now = time.monotonic()
            # Say so if an input hasn't attached - after 15s, then every 10 min.
            if waiting and now - started > 15 and now - warned_at > 600:
                warned_at = now
                for b in waiting:
                    log.warning('Still waiting for the Phidget: %s. Is it plugged in, and '
                                'closed in the Phidget Control Panel?', b.label)
    except KeyboardInterrupt:
        pass
    finally:
        for b in buttons:
            b.close()
        log.info('Stopped.')


if __name__ == '__main__':
    main()
