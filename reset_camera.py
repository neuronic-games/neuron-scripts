#!/usr/bin/env python
"""Reset the webcam by power-cycling its USB port on a StarTech managed
hub, then toggling it in OBS - reproduces the confirmed-working manual fix
(physical unplug/replug, then OBS Deactivate/Activate) entirely from
software. Standalone/independent of open_projector.py - run this on its
own, e.g. manually when the camera's dead, or from a monitoring script
later.

--- Hardware step ---
Requires a StarTech managed USB hub (5G4AINDRM-USB-A-HUB) with its
"USB Hub Administrator" software installed, which provides the CUSBC.exe
command-line tool used here to power-cycle a specific port.

Before relying on this script:
  1. Run `CUSBC /Q` manually to find which COM port the hub enumerated as,
     and confirm which port number the camera is plugged into.
  2. Set HUB_COM_PORT and HUB_CAMERA_PORT below (or via environment
     variables) to those values.
  3. If CUSBC.exe's install folder isn't on your PATH, set CUSBC_PATH to
     its full path.
  4. Confirm `CUSBC /S:COMn 0:<port>` then `1:<port>` actually revives the
     camera before trusting this script - StarTech's docs describe this
     as port enable/disable, not explicitly a guaranteed true power cut.

--- OBS step ---
Requires: pip install obsws-python
Requires OBS's WebSocket server enabled (Tools > WebSocket Server Settings
in OBS), with OBS_PASSWORD set below if it has one configured.

Everything is logged to reset_camera.log next to this script.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time

import obsws_python as obs

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_SCRIPT_DIR, "reset_camera.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(_LOG_FILE, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# --- StarTech hub settings ---
# Full path to CUSBC.exe. Leave as "CUSBC" if its install folder is on PATH.
CUSBC_PATH = os.getenv("CUSBC_PATH", "CUSBC")
# COM port the hub enumerates as - find via `CUSBC /Q`. MUST be set before
# this script will do anything (see module docstring).
HUB_COM_PORT = os.getenv("HUB_COM_PORT", "")
# Which hub port the camera is plugged into (per CUSBC /Q output).
HUB_CAMERA_PORT = os.getenv("HUB_CAMERA_PORT", "1")
# How long to leave the port powered off before restoring it.
HUB_POWER_OFF_SEC = int(os.getenv("HUB_POWER_OFF_SEC", "3"))
# Extra time to let Windows re-enumerate the device after power is restored,
# before OBS tries to touch it.
POST_POWER_ON_SETTLE_SEC = int(os.getenv("POST_POWER_ON_SETTLE_SEC", "3"))

# --- OBS settings ---
HOST = os.getenv("OBS_HOST", "127.0.0.1")
PORT = int(os.getenv("OBS_PORT", "4455"))
PASSWORD = os.getenv("OBS_PASSWORD", "")
CAMERA_NAME = os.getenv("OBS_CAMERA_SOURCE", "Integrated Webcam")
CAMERA_TOGGLE_OFF_SEC = 1
OBS_CONNECT_TIMEOUT_SEC = 30
OBS_CONNECT_RETRY_DELAY_SEC = 2


def run_cusbc(*args: str) -> str:
    cmd = [CUSBC_PATH, *args]
    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        log.info("stdout: %s", result.stdout.strip())
    if result.stderr.strip():
        log.warning("stderr: %s", result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"CUSBC exited with code {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def power_cycle_camera_port() -> None:
    if not HUB_COM_PORT:
        raise RuntimeError(
            "HUB_COM_PORT is not set. Run `CUSBC /Q` to find it, then set "
            "the HUB_COM_PORT environment variable (e.g. COM3)."
        )

    log.info("Powering OFF hub port %s on %s...", HUB_CAMERA_PORT, HUB_COM_PORT)
    run_cusbc(f"/S:{HUB_COM_PORT}", f"0:{HUB_CAMERA_PORT}")

    log.info("Waiting %ss with power off...", HUB_POWER_OFF_SEC)
    time.sleep(HUB_POWER_OFF_SEC)

    log.info("Powering ON hub port %s on %s...", HUB_CAMERA_PORT, HUB_COM_PORT)
    run_cusbc(f"/S:{HUB_COM_PORT}", f"1:{HUB_CAMERA_PORT}")

    log.info("Waiting %ss for Windows to re-enumerate the device...", POST_POWER_ON_SETTLE_SEC)
    time.sleep(POST_POWER_ON_SETTLE_SEC)


def wait_for_obs() -> obs.ReqClient:
    deadline = time.time() + OBS_CONNECT_TIMEOUT_SEC
    last_error = None
    while time.time() < deadline:
        try:
            return obs.ReqClient(host=HOST, port=PORT, password=PASSWORD, timeout=5)
        except Exception as e:
            last_error = e
            time.sleep(OBS_CONNECT_RETRY_DELAY_SEC)
    raise RuntimeError(
        f"Could not connect to OBS WebSocket at {HOST}:{PORT} after "
        f"{OBS_CONNECT_TIMEOUT_SEC}s: {last_error}"
    )


def toggle_camera_in_obs() -> None:
    client = wait_for_obs()
    scene_name = client.get_current_program_scene().current_program_scene_name
    log.info("Current program scene: %s", scene_name)

    try:
        item_id = client.get_scene_item_id(scene_name, CAMERA_NAME).scene_item_id
    except Exception as e:
        log.warning("Could not find source '%s' in scene '%s': %s", CAMERA_NAME, scene_name, e)
        return

    log.info("Toggling '%s' (scene item %s) off/on in OBS...", CAMERA_NAME, item_id)
    client.set_scene_item_enabled(scene_name, item_id, False)
    time.sleep(CAMERA_TOGGLE_OFF_SEC)
    client.set_scene_item_enabled(scene_name, item_id, True)


def main() -> None:
    log.info("=== reset_camera.py starting ===")
    power_cycle_camera_port()
    toggle_camera_in_obs()
    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
        raise
