#!/usr/bin/env python
"""Startup workarounds for OBS race conditions, run once shortly after OBS
launches (see start_obs.cmd).

1. Opens the Program projector ourselves via obs-websocket, instead of
   relying on OBS's native "Save projectors on exit" restore, which opens
   the projector before OBS renders its first frame and leaves it stuck on
   a black screen. See:
   https://github.com/obsproject/obs-studio/issues/5083
   https://github.com/obsproject/obs-studio/issues/8729
   Turn OFF "Save projectors on exit" in OBS (Settings > General >
   Projectors) so OBS doesn't also open its own stuck/black projector.

2. Nudges the webcam source (toggles it off then on, retrying over a
   window in case the USB device itself isn't enumerated yet) to force OBS
   to close and reopen its DirectShow device handle. Previously this
   required a physical unplug/replug of the camera after OBS started -
   toggling the source reproduces that in software.
   REQUIRES "Deactivate when not showing" to be checked in the camera
   source's Properties in OBS - without it, OBS keeps the device handle
   open continuously and toggling visibility has no effect.

Since this runs detached (start "" in start_obs.cmd) with no visible
console, everything is also logged to open_projector.log next to this
script - check that file to see what actually happened on a given run.

Requires: pip install obsws-python
Requires OBS's WebSocket server to be enabled (Tools > WebSocket Server
Settings in OBS), with OBS_PASSWORD set below if it has one configured.
"""

from __future__ import annotations

import logging
import os
import time

import obsws_python as obs

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_SCRIPT_DIR, "open_projector.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(_LOG_FILE, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

HOST = os.getenv("OBS_HOST", "127.0.0.1")
PORT = int(os.getenv("OBS_PORT", "4455"))
PASSWORD = os.getenv("OBS_PASSWORD", "")

# --- Projector ---
# Which monitor (0-indexed, per OBS's own GetMonitorList) to open the
# projector fullscreen on. "Program" = the final mixed output.
MONITOR_INDEX = int(os.getenv("OBS_PROJECTOR_MONITOR", "2"))
VIDEO_MIX_TYPE = "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM"

# --- Camera reconnect ---
CAMERA_NAME = os.getenv("OBS_CAMERA_SOURCE", "Integrated Webcam")
CAMERA_TOGGLE_OFF_SEC = 1        # how long to leave it disabled before re-enabling
CAMERA_RETRY_WINDOW_SEC = 60     # keep retrying the toggle for up to this long
CAMERA_RETRY_INTERVAL_SEC = 10   # how often to retry within that window

CONNECT_TIMEOUT_SEC = 60       # give up after this long waiting for OBS
CONNECT_RETRY_DELAY_SEC = 2
STARTUP_SETTLE_DELAY_SEC = 5   # extra wait after connecting, before doing
                                # anything, so OBS has actually rendered at
                                # least one real frame


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


def _toggle_camera_once(client: obs.ReqClient, scene_name: str, item_id: int) -> None:
    client.set_scene_item_enabled(scene_name, item_id, False)
    time.sleep(CAMERA_TOGGLE_OFF_SEC)
    client.set_scene_item_enabled(scene_name, item_id, True)


def reconnect_camera(client: obs.ReqClient) -> None:
    scene_name = client.get_current_program_scene().current_program_scene_name
    log.info("Current program scene: %s", scene_name)

    try:
        item_id = client.get_scene_item_id(scene_name, CAMERA_NAME).scene_item_id
    except Exception as e:
        log.warning("Could not find source '%s' in scene '%s': %s", CAMERA_NAME, scene_name, e)
        log.warning("Check OBS_CAMERA_SOURCE matches the exact source name in OBS.")
        return

    log.info("Found '%s' as scene item %s in '%s'.", CAMERA_NAME, item_id, scene_name)

    # Retry over a window rather than once - if the USB device itself
    # isn't enumerated by Windows yet, toggling OBS's handle to it won't
    # help until it is, no matter how correctly OBS is configured.
    deadline = time.time() + CAMERA_RETRY_WINDOW_SEC
    attempt = 0
    while True:
        attempt += 1
        log.info("Toggling '%s' off/on (attempt %d)...", CAMERA_NAME, attempt)
        try:
            _toggle_camera_once(client, scene_name, item_id)
        except Exception:
            log.exception("Error while toggling '%s'", CAMERA_NAME)

        if time.time() >= deadline:
            break
        time.sleep(CAMERA_RETRY_INTERVAL_SEC)

    log.info(
        "Camera reconnect attempts finished (%d attempts over ~%ds). "
        "This does not confirm the camera is actually producing video - "
        "check the source in OBS.",
        attempt, CAMERA_RETRY_WINDOW_SEC,
    )


def main() -> None:
    log.info("=== open_projector.py starting ===")
    log.info("Waiting for OBS WebSocket at %s:%s ...", HOST, PORT)
    client = wait_for_obs()

    log.info("Connected. Waiting %ss more for OBS to finish rendering...", STARTUP_SETTLE_DELAY_SEC)
    time.sleep(STARTUP_SETTLE_DELAY_SEC)

    open_projector(client)
    reconnect_camera(client)

    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
