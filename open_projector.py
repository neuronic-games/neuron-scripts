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

2. Nudges the webcam source (toggles it off then on) to force OBS to close
   and reopen its DirectShow device handle. Previously this required a
   physical unplug/replug of the camera after OBS started - toggling the
   source reproduces that in software.
   REQUIRES "Deactivate when not showing" to be checked in the camera
   source's Properties in OBS - without it, OBS keeps the device handle
   open continuously and toggling visibility has no effect. Enable it
   once, manually, in OBS.

Requires: pip install obsws-python
Requires OBS's WebSocket server to be enabled (Tools > WebSocket Server
Settings in OBS), with OBS_PASSWORD set below if it has one configured.
"""

from __future__ import annotations

import os
import time

import obsws_python as obs

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
CAMERA_TOGGLE_OFF_SEC = 1  # how long to leave it disabled before re-enabling

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
    print(f"Opening {VIDEO_MIX_TYPE} projector on monitor index {MONITOR_INDEX}...")
    client.open_video_mix_projector(VIDEO_MIX_TYPE, monitor_index=MONITOR_INDEX)


def reconnect_camera(client: obs.ReqClient) -> None:
    scene_name = client.get_current_program_scene().current_program_scene_name
    try:
        item_id = client.get_scene_item_id(scene_name, CAMERA_NAME).scene_item_id
    except Exception as e:
        print(f"Could not find '{CAMERA_NAME}' in current scene '{scene_name}': {e}")
        return

    print(f"Toggling '{CAMERA_NAME}' in scene '{scene_name}' to force a device reconnect...")
    client.set_scene_item_enabled(scene_name, item_id, False)
    time.sleep(CAMERA_TOGGLE_OFF_SEC)
    client.set_scene_item_enabled(scene_name, item_id, True)


def main() -> None:
    print(f"Waiting for OBS WebSocket at {HOST}:{PORT} ...")
    client = wait_for_obs()

    print(f"Connected. Waiting {STARTUP_SETTLE_DELAY_SEC}s more for OBS to finish rendering...")
    time.sleep(STARTUP_SETTLE_DELAY_SEC)

    open_projector(client)
    reconnect_camera(client)

    print("Done.")


if __name__ == "__main__":
    main()
