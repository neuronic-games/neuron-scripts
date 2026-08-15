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

Note: the webcam-not-reconnecting-on-startup problem is handled
separately, by reset_camera.py - toggling the source in OBS alone isn't
enough to bring the camera back, it needs an actual USB-level power cycle.
Run reset_camera.py independently when the camera needs reviving.

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


def main() -> None:
    log.info("=== open_projector.py starting ===")
    log.info("Waiting for OBS WebSocket at %s:%s ...", HOST, PORT)
    client = wait_for_obs()

    log.info("Connected. Waiting %ss more for OBS to finish rendering...", STARTUP_SETTLE_DELAY_SEC)
    time.sleep(STARTUP_SETTLE_DELAY_SEC)

    open_projector(client)

    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
