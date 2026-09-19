#!/usr/bin/env python
"""Forces OBS's "Save Projectors on Exit" setting off, run synchronously
right before OBS launches each time (see start_obs.cmd) - before the
settings-backup restore that runs earlier in start_obs.cmd, this had to
be set manually in the OBS UI, and it was easy for it to drift back to
true (or for a stale settings-backup to reintroduce true) without anyone
noticing until the blank-duplicate-projector bug showed up again.

Why this setting needs to be forced off: OBS's own native "restore saved
projectors on launch" behavior (gated by this checkbox) opens projectors
before OBS renders its first frame, leaving them stuck permanently
blank - see open_projector.py's docstring for the full story and the
workaround it uses instead (reading the same saved-projector data itself
and opening/fixing each one via obs-websocket).

This script is deliberately independent from that data: the projector
list open_projector.py reads lives in the active scene collection's own
file (e.g. "%APPDATA%\\obs-studio\\basic\\scenes\\Untitled.json", key
"saved_projectors"), which is untouched by this script. This one only
touches the *checkbox* - a separate file/setting entirely - so forcing it
off here can never affect which projectors open_projector.py opens.

Confirmed on a real deployment (OBS 32.x): the checkbox lives in
    %APPDATA%\\obs-studio\\user.ini
under:
    [BasicWindow]
    SaveProjectors=true|false
Older OBS versions may keep the same section/key in global.ini instead
(the two were split apart into a per-machine/per-user pair at some point)
- this script checks user.ini first (if present), then falls back to
global.ini.

Edits the file line-by-line rather than via a full ini parse-and-rewrite,
so it only touches the one SaveProjectors line (or inserts it) and
leaves every other line - including OBS's own formatting/ordering,
and any values containing "%" that would trip up a naive ini parser's
interpolation - completely untouched.
"""

from __future__ import annotations

import os
import re
import sys

_IS_WIN = sys.platform == 'win32'

SECTION = "BasicWindow"
KEY = "SaveProjectors"

_SECTION_RE = re.compile(r"^\s*\[(.+?)\]\s*$")
_KEY_RE = re.compile(r"^\s*%s\s*=\s*(.*?)\s*$" % re.escape(KEY), re.IGNORECASE)


def _config_path():
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None
    user_ini = os.path.join(appdata, "obs-studio", "user.ini")
    if os.path.isfile(user_ini):
        return user_ini
    global_ini = os.path.join(appdata, "obs-studio", "global.ini")
    if os.path.isfile(global_ini):
        return global_ini
    return None


def _force_false(path: str) -> bool:
    """Set [BasicWindow] SaveProjectors=false in the ini file at path,
    inserting the section/key if missing. Returns True if the file was
    changed, False if it already said false."""
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    section_start = None
    section_end = len(lines)
    key_line_idx = None
    current_value = None

    in_section = False
    for i, line in enumerate(lines):
        m = _SECTION_RE.match(line)
        if m:
            if in_section:
                section_end = i
                break
            if m.group(1) == SECTION:
                in_section = True
                section_start = i
            continue
        if in_section:
            km = _KEY_RE.match(line)
            if km:
                key_line_idx = i
                current_value = km.group(1)

    if section_start is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append("[%s]\n" % SECTION)
        lines.append("%s=false\n" % KEY)
        changed = True
    elif key_line_idx is None:
        lines.insert(section_start + 1, "%s=false\n" % KEY)
        changed = True
    elif current_value is not None and current_value.strip().lower() == "false":
        changed = False
    else:
        lines[key_line_idx] = "%s=false\n" % KEY
        changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return changed


def main() -> int:
    if not _IS_WIN:
        print("Not on Windows - nothing to do.")
        return 0

    path = _config_path()
    if not path:
        print(
            "Could not find OBS's user.ini/global.ini under "
            "%APPDATA%\\obs-studio - OBS may not have been run on this "
            "machine yet. Skipping."
        )
        return 0

    try:
        changed = _force_false(path)
    except Exception as e:
        print("Failed to patch %s: %s" % (path, e))
        return 1

    if changed:
        print("Set [%s] %s=false in %s." % (SECTION, KEY, path))
    else:
        print("[%s] %s was already false in %s - nothing to do." % (SECTION, KEY, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
