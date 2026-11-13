#!/usr/bin/env python
# obs_projectors.py
# Neuronic 2026
#
# Keeps OBS's saved projector list from being lost by backup_obs_settings.cmd.
#
# OBS stores which projectors are open (and on which monitor) in each scene
# collection file, "basic\scenes\<name>.json", under "saved_projectors" -
# but only writes it when "Save projectors on exit" is on. start_obs.cmd
# turns that setting off at every launch (OBS's own projector restore opens
# them blank - see open_projector.py), and with it off OBS empties the list
# in its live files. So a plain backup copied an EMPTY list over the good
# one in the backup, and open_projector.py then only opened a single
# Program projector.
#
# backup_obs_settings.cmd runs:
#   obs_projectors.py keep     - before copying: remember the lists in the backup
#   obs_projectors.py restore  - after copying: put back any list that came
#                                over empty. A non-empty list from OBS (saved
#                                on purpose with "Save projectors on exit" on)
#                                replaces the old one.
#   obs_projectors.py show     - list the projectors in the backup.

import glob
import json
import os
import sys
import tempfile

BACKUP_SCENES = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')),
                             'Documents', 'Neuronic', 'settings-backup',
                             'obs-studio', 'basic', 'scenes')
KEPT = os.path.join(tempfile.gettempdir(), 'neuron-obs-projectors.json')
TYPES = {0: 'Source', 1: 'Scene', 2: 'Preview', 3: 'Program', 4: 'Multiview'}


def _scene_files():
    return sorted(f for f in glob.glob(os.path.join(BACKUP_SCENES, '*.json')))


def _read(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def _describe(entries):
    out = []
    for e in entries:
        kind = TYPES.get(e.get('type'), f"type {e.get('type')}")
        name = f" '{e['name']}'" if e.get('name') else ''
        out.append(f"{kind}{name} on monitor {e.get('monitor')}")
    return ', '.join(out) if out else '(none)'


def keep():
    kept = {}
    for path in _scene_files():
        try:
            entries = _read(path).get('saved_projectors') or []
        except Exception as e:
            print(f'  Could not read {os.path.basename(path)}: {e}')
            continue
        if entries:
            kept[os.path.basename(path)] = entries
    with open(KEPT, 'w', encoding='utf-8') as f:
        json.dump(kept, f)
    for name, entries in kept.items():
        print(f'  Saved projector list in the backup ({name}): {_describe(entries)}')


def restore():
    try:
        with open(KEPT, 'r', encoding='utf-8') as f:
            kept = json.load(f)
    except FileNotFoundError:
        kept = {}
    for path in _scene_files():
        name = os.path.basename(path)
        try:
            data = _read(path)
        except Exception as e:
            print(f'  Could not read {name}: {e}')
            continue
        new = data.get('saved_projectors') or []
        old = kept.get(name) or []
        if new:
            if new != old:
                print(f'  Projector list updated from OBS ({name}): {_describe(new)}')
        elif old:
            data['saved_projectors'] = old
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f'  Kept the existing projector list ({name}): {_describe(old)}')
        else:
            print(f'  WARNING: no saved projectors in {name} - Launch will only open '
                  'one Program projector. See "Projectors" in the README.')
    try:
        os.remove(KEPT)
    except OSError:
        pass


def show():
    files = _scene_files()
    if not files:
        print(f'No OBS settings backup found in {BACKUP_SCENES}')
    for path in files:
        try:
            entries = _read(path).get('saved_projectors') or []
        except Exception as e:
            entries = []
            print(f'  Could not read {os.path.basename(path)}: {e}')
        print(f'{os.path.basename(path)}: {_describe(entries)}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    {'keep': keep, 'restore': restore, 'show': show}.get(cmd, show)()
