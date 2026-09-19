#!/usr/bin/env python
"""Reset the webcam by power-cycling its USB port on a StarTech managed
hub, then toggling it in OBS a few times - reproduces the confirmed-working
manual fix (physical unplug/replug, then a couple of OBS Deactivate/
Activate passes) entirely from software.

Run in TWO SEPARATE synchronous steps from start_obs.cmd, with
open_projector.py run in between - gated by settings.resetCameraOnStart
(a no-op that just logs and exits immediately when False, without even
connecting to OBS - harmless to always call regardless of whether a given
deployment has a camera/hub at all):

    reset_camera.py power-cycle    (before open_projector.py)
    open_projector.py
    reset_camera.py toggle         (after open_projector.py)

Why split like this: the OBS-side toggle only actually reinitializes the
capture device if the scene containing it is currently being shown by
something (Program, Preview, or an open projector) at the moment of the
toggle - confirmed on a real deployment where the camera lived in a scene
that's neither Program nor Preview at boot, only reachable via its own
dedicated projector. Toggling before that projector was ever opened did
nothing (no error - the API call just doesn't reinitialize the device
when nothing's watching that scene), and no amount of retrying to
close/reopen the projector window afterward fixed it either (that fixes
a different bug - a stuck window render target - not a device that was
never actually reinitialized in the first place). Toggling again once the
projector was open (matching the user's own manual deactivate/reactivate
fix) is what actually worked. Running with no argument does both steps
back to back, which is fine for a manual/standalone run where the camera
is likely already shown by something.

--- Hardware step ---
Requires a StarTech managed USB hub (5G4AINDRM-USB-A-HUB) with its
"USB Hub Administrator" software installed, which provides the CUSBC.exe
command-line tool used here to power-cycle a specific port.

Before relying on this script:
  1. Run `CUSBC /Q` manually to find which COM port the hub enumerated as,
     and confirm which port number the camera is plugged into.
  2. Set settings.cameraHubComPort and settings.cameraHubPort in
     settings.py to those values (that's the file to edit per deployment,
     not this script).
  3. If CUSBC.exe's install folder isn't on PATH, set
     settings.cameraHubCusbcPath to its full path.
  4. Confirm `CUSBC /S:COMn 0:<port>` then `1:<port>` actually revives the
     camera before trusting this script - StarTech's docs describe this
     as port enable/disable, not explicitly a guaranteed true power cut.
     CONFIRMED on the 5G4AINDRM-USB-A-HUB: only port 1 does a real VBUS
     power cut (verified via Device Manager - the camera actually
     disappears/reappears there). Other ports only disable the data
     lines, which does NOT reset the camera's firmware and will not fix
     an ELP-style enumeration issue. Use port 1 on that hub model.

--- OBS step ---
Requires: pip install obsws-python
Requires OBS's WebSocket server enabled (Tools > WebSocket Server Settings
in OBS), with settings.obsPassword set if it has one configured.

Everything is logged to reset_camera.log next to this script.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time

import obsws_python as obs

import settings_loader  # must run before `import settings` below
import settings

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_SCRIPT_DIR, "reset_camera.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(_LOG_FILE, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# --- StarTech hub settings (from settings.py) ---
# Full path to CUSBC.exe. Leave as "CUSBC" if its install folder is on PATH.
CUSBC_PATH = getattr(settings, "cameraHubCusbcPath", "CUSBC")
# COM port the hub enumerates as - find via `CUSBC /Q`. MUST be set before
# this script will do anything (see module docstring).
HUB_COM_PORT = getattr(settings, "cameraHubComPort", "")
# Which hub port the camera is plugged into (per CUSBC /Q output).
HUB_CAMERA_PORT = getattr(settings, "cameraHubPort", "1")
# How long to leave the port powered off before restoring it.
HUB_POWER_OFF_SEC = int(getattr(settings, "cameraHubPowerOffSec", 5))
# Extra time to let Windows re-enumerate the device after power is restored,
# before OBS tries to touch it.
POST_POWER_ON_SETTLE_SEC = int(os.getenv("POST_POWER_ON_SETTLE_SEC", "5"))

# --- OBS settings (from settings.py) ---
HOST = getattr(settings, "obsHost", "127.0.0.1")
PORT = int(getattr(settings, "obsPort", 4455))
PASSWORD = getattr(settings, "obsPassword", "")
CAMERA_NAME = getattr(settings, "cameraSource", "Integrated Webcam")
CAMERA_TOGGLE_OFF_SEC = 1
OBS_CONNECT_TIMEOUT_SEC = 30
OBS_CONNECT_RETRY_DELAY_SEC = 2
# With a genuine VBUS power cut (confirmed hub port 1 - see settings.py's
# cameraHubPort comment), a single off/on toggle in OBS is enough. Multiple
# retries were only needed to compensate for hub ports that only did a
# soft/data-line disconnect instead of a real power cut. Kept configurable
# in case a different hub/port ends up needing more than one pass again.
CAMERA_TOGGLE_ATTEMPTS = int(os.getenv("CAMERA_TOGGLE_ATTEMPTS", "1"))
CAMERA_TOGGLE_RETRY_INTERVAL_SEC = int(os.getenv("CAMERA_TOGGLE_RETRY_INTERVAL_SEC", "5"))


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


def find_camera_scene(client: obs.ReqClient, source_name: str):
    """Find a scene containing a scene item named source_name, so the
    camera can be toggled even when it only lives in a scene that isn't
    the current Program scene at boot (e.g. a dedicated "Raw Scene" that
    gets opened via its own projector, separate from whatever Program
    happens to be showing at startup - confirmed on a real deployment
    where this mismatch silently skipped the toggle entirely). Checks
    the current program scene first (fast path, and matches the
    original/common case), then falls back to scanning every scene.
    Returns (scene_name, scene_item_id), or (None, None) if not found
    anywhere."""
    try:
        program_scene = client.get_current_program_scene().current_program_scene_name
    except Exception:
        program_scene = None

    if program_scene:
        try:
            item_id = client.get_scene_item_id(program_scene, source_name).scene_item_id
            return program_scene, item_id
        except Exception:
            log.info(
                "'%s' not in current program scene '%s' - checking other scenes...",
                source_name, program_scene,
            )

    try:
        scene_names = [s["sceneName"] for s in client.get_scene_list().scenes]
    except Exception:
        log.exception("Could not get the scene list from OBS")
        return None, None

    for scene_name in scene_names:
        if scene_name == program_scene:
            continue  # already checked above
        try:
            item_id = client.get_scene_item_id(scene_name, source_name).scene_item_id
            return scene_name, item_id
        except Exception:
            continue

    return None, None


def toggle_camera_in_obs() -> None:
    client = wait_for_obs()

    scene_name, item_id = find_camera_scene(client, CAMERA_NAME)
    if item_id is None:
        log.warning("Could not find source '%s' in any scene - nothing to toggle.", CAMERA_NAME)
        return
    log.info("Found '%s' in scene '%s' (scene item %s)", CAMERA_NAME, scene_name, item_id)

    for attempt in range(1, CAMERA_TOGGLE_ATTEMPTS + 1):
        log.info(
            "Toggling '%s' (scene item %s) off/on in OBS (attempt %d/%d)...",
            CAMERA_NAME, item_id, attempt, CAMERA_TOGGLE_ATTEMPTS,
        )
        client.set_scene_item_enabled(scene_name, item_id, False)
        time.sleep(CAMERA_TOGGLE_OFF_SEC)
        client.set_scene_item_enabled(scene_name, item_id, True)

        if attempt < CAMERA_TOGGLE_ATTEMPTS:
            time.sleep(CAMERA_TOGGLE_RETRY_INTERVAL_SEC)


def main(argv=None) -> None:
    """Usage: reset_camera.py [power-cycle|toggle]

    With no argument, does both steps back to back (the original
    behavior - fine for a manual/standalone run, or for a camera that's
    already actively shown by something in OBS when this runs).

    start_obs.cmd instead calls the two steps separately, with
    open_projector.py run in between - see that .cmd file's comments and
    this module's docstring for why: the OBS-side toggle only actually
    reinitializes the capture device if the scene containing it is
    currently being shown by something (Program, Preview, or an open
    projector) at the moment of the toggle. Confirmed on a real
    deployment where the camera lived in a scene that's neither Program
    nor Preview at boot (only reachable via its own dedicated
    projector): toggling before that projector was open did nothing
    (silently - no error, the API call just doesn't reinitialize the
    device when the scene isn't showing), and no amount of retrying to
    close/reopen the projector window afterward fixed it either, since
    the device itself had genuinely never been reinitialized - only
    toggling it again once the projector was actually open (matching the
    user's own manual deactivate/reactivate fix) worked.
    """
    argv = sys.argv[1:] if argv is None else argv
    mode = argv[0] if argv else "both"
    if mode not in ("both", "power-cycle", "toggle"):
        raise SystemExit("Usage: reset_camera.py [power-cycle|toggle]")

    log.info("=== reset_camera.py starting (mode=%s) ===", mode)

    if not getattr(settings, "resetCameraOnStart", False):
        log.info("settings.resetCameraOnStart is False - nothing to do.")
        return

    if mode in ("both", "power-cycle"):
        power_cycle_camera_port()
    if mode in ("both", "toggle"):
        toggle_camera_in_obs()
    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
        raise
