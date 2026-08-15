#!/usr/bin/env python
"""Open the OBS Program projector a few seconds after OBS finishes starting.

Works around a long-standing OBS bug where a projector restored via "Save
projectors on exit" opens before OBS renders its first frame and gets
stuck showing a permanently black frame - see e.g.
https://github.com/obsproject/obs-studio/issues/5083 and
https://github.com/obsproject/obs-studio/issues/8729. Opening the
projector ourselves via obs-websocket, well after OBS is fully up, avoids
the race entirely.

Because of this, turn OFF "Save projectors on exit" in OBS (Settings >
General > Projectors) - otherwise OBS will still auto-open its own
(stuck/black) projector in addition to the one this script opens.

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

# Which monitor (0-indexed, per OBS's own GetMonitorList) to open the
# projector fullscreen on.
MONITOR_INDEX = int(os.getenv("OBS_PROJECTOR_MONITOR", "2"))

# "Program" = the final mixed output (what's being recorded/streamed/sent
# to the virtual cam). Other options: OBS_WEBSOCKET_VIDEO_MIX_TYPE_PREVIEW,
# OBS_WEBSOCKET_VIDEO_MIX_TYPE_MULTIVIEW.
VIDEO_MIX_TYPE = "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM"

CONNECT_TIMEOUT_SEC = 60       # give up after this long waiting for OBS
CONNECT_RETRY_DELAY_SEC = 2
STARTUP_SETTLE_DELAY_SEC = 5   # extra wait after connecting, before opening
                                # the projector, so OBS has actually
                                # rendered at least one real frame


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


def main() -> None:
    print(f"Waiting for OBS WebSocket at {HOST}:{PORT} ...")
    client = wait_for_obs()

    print(f"Connected. Waiting {STARTUP_SETTLE_DELAY_SEC}s more for OBS to finish rendering...")
    time.sleep(STARTUP_SETTLE_DELAY_SEC)

    print(f"Opening {VIDEO_MIX_TYPE} projector on monitor index {MONITOR_INDEX}...")
    client.open_video_mix_projector(VIDEO_MIX_TYPE, monitor_index=MONITOR_INDEX)
    print("Done.")


if __name__ == "__main__":
    main()
