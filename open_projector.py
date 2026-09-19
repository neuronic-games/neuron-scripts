#!/usr/bin/env python
"""Startup workaround for an OBS race condition, run once shortly after OBS
launches (see start_obs.cmd).

Opens projectors ourselves via obs-websocket, instead of relying on OBS's
native "Save projectors on exit" restore, which opens them before OBS
renders its first frame and leaves them stuck on a black screen. See:
https://github.com/obsproject/obs-studio/issues/5083
https://github.com/obsproject/obs-studio/issues/8729
Turn OFF "Save projectors on exit" in OBS (Settings > General >
Projectors) so OBS doesn't also open its own stuck/black projectors.

Even opened this way (after waiting for OBS to connect, plus an extra
settle delay), a projector window can still come up permanently blank -
this is the same underlying OBS/Qt bug, just less likely to hit. Confirmed
on a real deployment that this is not a "hasn't been asked to repaint yet"
problem: neither minimizing/restoring nor shrink-then-resize (both of
which force a genuine Qt resizeEvent) fix it. So whatever's actually
broken is the render target/output OBS attached to that specific
projector instance at creation time, during the startup race - not
something a resize-driven repaint can fix from outside. The one thing
that IS reported to reliably fix it is closing that broken projector and
opening a fresh one, since a newly-created projector goes through OBS's
normal (working) setup path again - and by the time we do this, OBS has
had several more seconds to finish starting up, so the same race is much
less likely to hit twice. Since this runs unattended, on Windows we do
that ourselves for each projector: find its window by title, close it,
then ask OBS to open a new one in its place.

Which projectors get opened is NOT configured in settings.py - it's read
straight from OBS's own saved-projector list, the same data behind its
"Save projectors on exit" feature (turned off above only to stop OBS's
own broken auto-restore; the data itself is still what we key off of).
That list lives in the active scene collection's file, e.g.
"basic\\scenes\\Untitled.json", under the "saved_projectors" key - each
entry has a "type" (0=Source, 1=Scene, 2=Preview, 3=Program - see
obs-studio's ProjectorType enum) and "monitor" index, plus a "name" for
Source/Scene-type entries.

IMPORTANT: we read this from the settings BACKUP
("%USERPROFILE%\\Documents\\Neuronic\\settings-backup\\obs-studio\\basic\\
scenes\\..."), not OBS's live config under %APPDATA%. Confirmed on a real
deployment that OBS blanks saved_projectors in the live file within a few
seconds of loading a scene collection whenever SaveProjectors is false in
user.ini (which disable_obs_save_projectors.py now forces before every
launch, to stop OBS's own broken native restore - see above) - so by the
time this script gets around to checking, the live copy has often already
been wiped, even though it was correctly restored from the backup moments
earlier. The backup copy is never touched by a running OBS, so it's the
only reliable place to read this from. Falls back to the live path if no
backup folder exists at all (a deployment not using the backup/restore
mechanism).

To change which projectors open on startup: arrange them the way you want
in OBS (drag each projector to its monitor) with "Save projectors on
exit" temporarily turned back on, close OBS normally so it writes the
list, then run backup_obs_settings.cmd to refresh the backup with that
list (start_obs.cmd's restore step will otherwise keep overwriting your
live changes with the old backup anyway). No settings.py changes needed
for this.

If no saved projectors are found at all (e.g. a fresh machine with no
backup yet), this falls back to just opening the Program projector on
settings.obsProjectorMonitor.

Note: the webcam-not-reconnecting-on-startup problem is handled
separately, by reset_camera.py - toggling the source in OBS alone isn't
enough to bring the camera back, it needs an actual USB-level power cycle.
Run reset_camera.py independently when the camera needs reviving.

Since this runs detached (start "" in start_obs.cmd) with no visible
console, everything is also logged to open_projector.log next to this
script - check that file to see what actually happened on a given run.

Requires: pip install obsws-python
Requires OBS's WebSocket server to be enabled (Tools > WebSocket Server
Settings in OBS), with settings.obsPassword set if it has one configured.

Connection settings (obsHost, obsPort, obsPassword) and the
Program-projector fallback (obsProjectorMonitor) come from settings.py -
that's the file to edit per deployment, not this script.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import sys
import time

import obsws_python as obs

import settings_loader  # must run before `import settings` below
import settings

_IS_WIN = sys.platform == 'win32'
if _IS_WIN:
    import ctypes
    from ctypes import wintypes

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_SCRIPT_DIR, "open_projector.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(_LOG_FILE, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

HOST = getattr(settings, "obsHost", "127.0.0.1")
PORT = int(getattr(settings, "obsPort", 4455))
PASSWORD = getattr(settings, "obsPassword", "")

# Fallback only - used if OBS has no saved projectors at all yet (e.g. a
# brand new machine that's never had projectors arranged/saved in OBS).
PROGRAM_MONITOR_INDEX = int(getattr(settings, "obsProjectorMonitor", 2))

# Where to look for scene collection files - each one's own "name" field
# (checked against obs-websocket's reported current collection name)
# identifies which file is the active one, and its "saved_projectors"
# array is what we read. Checked in this order:
#   1. The settings BACKUP's copy - a static snapshot OBS never touches
#      while running, so it can't have been blanked out from under us
#      (see module docstring for why the live copy is unreliable here).
#   2. OBS's own live config, as a fallback for a deployment with no
#      settings-backup folder at all.
# Windows only.
_OBS_BACKUP_SCENES_DIR = (
    os.path.join(
        os.environ.get("USERPROFILE", ""),
        "Documents", "Neuronic", "settings-backup", "obs-studio", "basic", "scenes",
    ) if _IS_WIN else None
)
_OBS_LIVE_SCENES_DIR = (
    os.path.expandvars(r"%APPDATA%\obs-studio\basic\scenes") if _IS_WIN else None
)


def _scene_collections_dirs() -> list:
    dirs = []
    for d in (_OBS_BACKUP_SCENES_DIR, _OBS_LIVE_SCENES_DIR):
        if d and os.path.isdir(d):
            dirs.append(d)
    return dirs

# OBS's ProjectorType enum (frontend/widgets/OBSProjector.hpp) - the
# "type" value in each saved_projectors entry.
_TYPE_SOURCE = 0
_TYPE_SCENE = 1
_TYPE_PREVIEW = 2
_TYPE_PROGRAM = 3
_TYPE_MULTIVIEW = 4

CONNECT_TIMEOUT_SEC = 60       # give up after this long waiting for OBS
CONNECT_RETRY_DELAY_SEC = 2
STARTUP_SETTLE_DELAY_SEC = 5   # extra wait after connecting, before doing
                                # anything, so OBS has actually rendered at
                                # least one real frame

# --- Blank-projector fix (Windows only - see module docstring) ---
FIND_WINDOW_TIMEOUT_SEC = 10   # how long to wait for a projector window
                                # to actually appear before giving up
FIND_WINDOW_POLL_SEC = 0.5
CLOSE_TIMEOUT_SEC = 5          # how long to wait for the old projector
                                # window to actually finish closing
REOPEN_DELAY_SEC = 3           # extra pause after closing, before asking
                                # OBS to open a fresh one - gives OBS's
                                # video subsystem more time to be ready


def wait_for_obs() -> obs.ReqClient:
    deadline = time.time() + CONNECT_TIMEOUT_SEC
    last_error = None
    while time.time() < deadline:
        try:
            return obs.ReqClient(host=HOST, port=PORT, password=PASSWORD, timeout=5)
        except Exception as e:
            last_error = e
            time.sleep(CONNECT_RETRY_DELAY_SEC)
    raise RuntimeError(
        f"Could not connect to OBS WebSocket at {HOST}:{PORT} after "
        f"{CONNECT_TIMEOUT_SEC}s: {last_error}"
    )


def _find_scene_collection_file(collection_name: str):
    """Find the scene collection .json file matching collection_name, by
    checking each file's own "name" field - more reliable than trying to
    reconstruct OBS's filename-sanitizing rules ourselves. Searches the
    backup scenes dir first, then the live one (see
    _scene_collections_dirs). Returns the path, or None."""
    for scenes_dir in _scene_collections_dirs():
        for path in glob.glob(os.path.join(scenes_dir, "*.json")):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception:
                log.exception("Could not read/parse scene collection file %s", path)
                continue
            if data.get("name") == collection_name:
                return path
    return None


def _load_saved_projectors(client: obs.ReqClient) -> list:
    """Read the projector list OBS itself last saved for the active scene
    collection - see module docstring for why this (rather than
    settings.py fields) is what drives which projectors get opened, and
    why it's read from the settings backup rather than OBS's live
    config."""
    dirs = _scene_collections_dirs()
    if not dirs:
        return []

    try:
        info = client.get_scene_collection_list()
        collection_name = info.current_scene_collection_name
    except Exception:
        log.exception("Could not get the current scene collection name from OBS")
        return []

    path = _find_scene_collection_file(collection_name)
    if not path:
        log.warning(
            "Could not find the scene collection file for %r under any of %s - "
            "no saved projectors to open.", collection_name, dirs,
        )
        return []

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        log.exception("Could not read/parse scene collection file %s", path)
        return []

    saved = data.get("saved_projectors") or []
    log.info("Found %d saved projector(s) in %s", len(saved), path)
    return saved


def _spec_from_saved_entry(entry: dict):
    """Turn one saved_projectors entry into a spec dict: label (for
    logging), title_substrs (strings that must all appear in the
    projector's window title, to find/close it - OBS's title format has
    changed across versions, e.g. older "Fullscreen Projector (Program)"
    vs OBS 32.x "Projector - Program" - matching multiple required
    substrings survives that), and an open(client) callable. Returns
    None for anything we don't know how to (re)open (windowed
    projectors, Multiview, or a Source/Scene entry missing its name)."""
    ptype = entry.get("type")
    monitor = entry.get("monitor")
    name = entry.get("name")

    if monitor is None or monitor < 0:
        log.info("Skipping saved projector %r - not a fullscreen monitor projector.", entry)
        return None

    if ptype == _TYPE_PROGRAM:
        return {
            "label": "Program",
            "title_substrs": ("Projector", "Program"),
            "open": lambda client: client.open_video_mix_projector(
                "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM", monitor_index=monitor
            ),
        }

    if ptype == _TYPE_PREVIEW:
        return {
            "label": "Preview",
            "title_substrs": ("Projector", "Preview"),
            "open": lambda client: client.open_video_mix_projector(
                "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PREVIEW", monitor_index=monitor
            ),
        }

    if ptype == _TYPE_SOURCE:
        if not name:
            log.warning("Skipping a saved Source projector with no source name: %r", entry)
            return None
        return {
            "label": "Source: %s" % name,
            "title_substrs": ("Projector", "Source", name),
            "open": lambda client: client.open_source_projector(name, monitor_index=monitor),
        }

    if ptype == _TYPE_SCENE:
        # Scenes are just a special kind of source in OBS under the hood,
        # so the same OpenSourceProjector request works for them too -
        # only the window title ("Projector - Scene: <name>" rather than
        # "... Source: <name>") differs.
        if not name:
            log.warning("Skipping a saved Scene projector with no scene name: %r", entry)
            return None
        return {
            "label": "Scene: %s" % name,
            "title_substrs": ("Projector", "Scene", name),
            "open": lambda client: client.open_source_projector(name, monitor_index=monitor),
        }

    log.info("Skipping saved projector of unsupported type: %r", entry)
    return None


def _build_projector_specs(client: obs.ReqClient) -> list:
    specs = []
    for entry in _load_saved_projectors(client):
        spec = _spec_from_saved_entry(entry)
        if spec:
            specs.append(spec)

    if not specs:
        log.info(
            "No usable saved projectors found - falling back to opening "
            "Program on settings.obsProjectorMonitor=%s.", PROGRAM_MONITOR_INDEX,
        )
        specs.append({
            "label": "Program",
            "title_substrs": ("Projector", "Program"),
            "open": lambda client: client.open_video_mix_projector(
                "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM", monitor_index=PROGRAM_MONITOR_INDEX
            ),
        })

    return specs


def open_projector(client: obs.ReqClient, spec: dict) -> None:
    log.info("Opening %s projector...", spec["label"])
    try:
        spec["open"](client)
    except Exception:
        log.exception("Failed to open %s projector", spec["label"])


def _find_projector_hwnd(title_substrs, timeout_sec: float):
    """Poll for a top-level window whose title contains every string in
    title_substrs. Windows only. Returns the HWND, or None if it never
    showed up."""
    user32 = ctypes.windll.user32
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    found = {"hwnd": None}

    def _callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if all(substr in title for substr in title_substrs):
            found["hwnd"] = hwnd
            return False  # stop enumeration
        return True

    proc = EnumWindowsProc(_callback)
    deadline = time.time() + timeout_sec
    while time.time() < deadline and found["hwnd"] is None:
        user32.EnumWindows(proc, 0)
        if found["hwnd"] is None:
            time.sleep(FIND_WINDOW_POLL_SEC)
    return found["hwnd"]


def _close_window(hwnd) -> None:
    WM_CLOSE = 0x0010
    ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def _wait_until_closed(hwnd, timeout_sec: float) -> bool:
    user32 = ctypes.windll.user32
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not user32.IsWindow(hwnd):
            return True
        time.sleep(0.2)
    return not user32.IsWindow(hwnd)


def _reopen_if_blank(client: obs.ReqClient, spec: dict) -> None:
    """Close the projector window we just opened for this spec and open
    a fresh one in its place. Works around the OBS/Qt bug where a
    projector opened right at OBS startup renders permanently
    blank/black - see module docstring for why this (rather than a
    resize-driven repaint) is the actual fix. Windows only; a no-op
    elsewhere."""
    if not _IS_WIN:
        return

    hwnd = _find_projector_hwnd(spec["title_substrs"], FIND_WINDOW_TIMEOUT_SEC)
    if not hwnd:
        log.warning(
            "Could not find the %s projector window (title containing all of "
            "%r) within %ss to close/reopen it - it may come up blank. It may "
            "just need more time to appear, or its title may not match on "
            "this OBS version.",
            spec["label"], spec["title_substrs"], FIND_WINDOW_TIMEOUT_SEC,
        )
        return

    log.info("Closing %s projector window (hwnd=%s) so we can reopen it fresh...", spec["label"], hwnd)
    _close_window(hwnd)

    if not _wait_until_closed(hwnd, CLOSE_TIMEOUT_SEC):
        log.warning(
            "%s projector window (hwnd=%s) did not close within %ss - "
            "leaving it as-is, not attempting to reopen.",
            spec["label"], hwnd, CLOSE_TIMEOUT_SEC,
        )
        return

    log.info("Closed. Waiting %ss before opening a fresh %s projector...", REOPEN_DELAY_SEC, spec["label"])
    time.sleep(REOPEN_DELAY_SEC)
    open_projector(client, spec)


def main() -> None:
    log.info("=== open_projector.py starting ===")
    log.info("Waiting for OBS WebSocket at %s:%s ...", HOST, PORT)
    client = wait_for_obs()

    log.info("Connected. Waiting %ss more for OBS to finish rendering...", STARTUP_SETTLE_DELAY_SEC)
    time.sleep(STARTUP_SETTLE_DELAY_SEC)

    specs = _build_projector_specs(client)
    log.info("Opening %d projector(s): %s", len(specs), ", ".join(s["label"] for s in specs))

    for spec in specs:
        open_projector(client, spec)
        _reopen_if_blank(client, spec)

    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
