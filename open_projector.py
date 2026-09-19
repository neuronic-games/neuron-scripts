#!/usr/bin/env python
"""Startup workaround for an OBS race condition, run once shortly after OBS
launches (see start_obs.cmd).

Opens the Program projector ourselves via obs-websocket, instead of relying
on OBS's native "Save projectors on exit" restore, which opens the
projector before OBS renders its first frame and leaves it stuck on a
black screen. See:
https://github.com/obsproject/obs-studio/issues/5083
https://github.com/obsproject/obs-studio/issues/8729
Turn OFF "Save projectors on exit" in OBS (Settings > General >
Projectors) so OBS doesn't also open its own stuck/black projector.

Even opened this way (after waiting for OBS to connect, plus an extra
settle delay), the projector window can still come up permanently blank -
this is the same underlying OBS/Qt bug, just less likely to hit. A
projector window that's blank because nothing ever painted it doesn't
self-heal; it only starts showing video once something forces the OS to
recomposite it (e.g. manually resizing/minimizing it, or switching scenes
in the main OBS window). Since this runs unattended, on Windows we do
that nudge ourselves right after opening the projector: find its window
by title and minimize/restore it once, which forces its swap chain to be
recreated and the projector to actually start rendering.

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

Connection/projector settings (obsHost, obsPort, obsPassword,
obsProjectorMonitor) come from settings.py - that's the file to edit per
deployment, not this script.
"""

from __future__ import annotations

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

# --- Projector ---
# Which monitor (0-indexed, per OBS's own GetMonitorList) to open the
# projector fullscreen on. "Program" = the final mixed output.
MONITOR_INDEX = int(getattr(settings, "obsProjectorMonitor", 2))
VIDEO_MIX_TYPE = "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM"

CONNECT_TIMEOUT_SEC = 60       # give up after this long waiting for OBS
CONNECT_RETRY_DELAY_SEC = 2
STARTUP_SETTLE_DELAY_SEC = 5   # extra wait after connecting, before doing
                                # anything, so OBS has actually rendered at
                                # least one real frame

# --- Blank-projector nudge (Windows only - see module docstring) ---
# OBS's projector window title has changed across versions - older builds
# titled it "Fullscreen Projector (Program)", OBS 32.x titles it
# "Projector - Program". Match on both required substrings rather than
# one fixed string so this doesn't silently stop matching again on the
# next OBS version bump. The main OBS window ("OBS 32.2.2 - Profile:
# ...") never contains "Program", so this can't accidentally match it.
PROJECTOR_WINDOW_TITLE_SUBSTRS = ("Projector", "Program")
FIND_WINDOW_TIMEOUT_SEC = 10   # how long to wait for the projector window
                                # to actually appear before giving up
FIND_WINDOW_POLL_SEC = 0.5
NUDGE_SETTLE_SEC = 0.5         # pause between minimize and restore


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


def open_projector(client: obs.ReqClient) -> None:
    log.info("Opening %s projector on monitor index %s...", VIDEO_MIX_TYPE, MONITOR_INDEX)
    try:
        client.open_video_mix_projector(VIDEO_MIX_TYPE, monitor_index=MONITOR_INDEX)
    except Exception:
        log.exception("Failed to open projector")


def _find_projector_hwnd(title_substrs, timeout_sec: float):
    """Poll for a top-level window whose title contains every string in
    title_substrs, e.g. ("Projector", "Program") to match either
    "Fullscreen Projector (Program)" (older OBS) or "Projector - Program"
    (OBS 32.x). Windows only. Returns the HWND, or None if it never
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


def _nudge_projector_repaint() -> None:
    """Work around the OBS/Qt bug where a projector window opened
    programmatically renders permanently blank/black - never on its own,
    only once something forces Windows to recomposite it. Minimizing then
    restoring the window forces that recomposite (its swap chain gets
    recreated), without needing any actual user interaction. Windows
    only; a no-op elsewhere."""
    if not _IS_WIN:
        return

    hwnd = _find_projector_hwnd(PROJECTOR_WINDOW_TITLE_SUBSTRS, FIND_WINDOW_TIMEOUT_SEC)
    if not hwnd:
        log.warning(
            "Could not find the projector window (title containing all of %r) "
            "within %ss to nudge it - it may come up blank. It may just need "
            "more time to appear, or its title may not match on this OBS version.",
            PROJECTOR_WINDOW_TITLE_SUBSTRS, FIND_WINDOW_TIMEOUT_SEC,
        )
        return

    log.info("Found projector window (hwnd=%s) - minimizing/restoring to force a repaint...", hwnd)
    SW_MINIMIZE = 6
    SW_RESTORE = 9
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, SW_MINIMIZE)
    time.sleep(NUDGE_SETTLE_SEC)
    user32.ShowWindow(hwnd, SW_RESTORE)
    log.info("Nudge done.")


def main() -> None:
    log.info("=== open_projector.py starting ===")
    log.info("Waiting for OBS WebSocket at %s:%s ...", HOST, PORT)
    client = wait_for_obs()

    log.info("Connected. Waiting %ss more for OBS to finish rendering...", STARTUP_SETTLE_DELAY_SEC)
    time.sleep(STARTUP_SETTLE_DELAY_SEC)

    open_projector(client)
    _nudge_projector_repaint()

    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
