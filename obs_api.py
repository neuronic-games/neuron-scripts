#!/usr/bin/env python
"""Small stdout-based bridge between the AIR kiosk and OBS WebSocket 5.x."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from obsws_python import ReqClient


DEFAULT_HOST = os.getenv("OBS_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("OBS_PORT", "4455"))
DEFAULT_PASSWORD = os.getenv("OBS_PASSWORD", "")


def client(host: str = DEFAULT_HOST) -> ReqClient:
    return ReqClient(
        host=host or DEFAULT_HOST,
        port=DEFAULT_PORT,
        password=DEFAULT_PASSWORD,
        timeout=5,
    )


def scene_list(host: str) -> None:
    response = client(host).get_scene_list()
    print(",".join(scene["sceneName"] for scene in response.scenes))


def switch(scene_name: str, host: str) -> None:
    client(host).set_current_program_scene(scene_name)
    print("Scene Switched")


def active_scene_source(host: str) -> None:
    c = client(host)
    scene_name = c.get_current_program_scene().scene_name
    items = c.get_scene_item_list(scene_name).scene_items
    images = [item for item in items if item.get("inputKind") == "image_source"]
    print(images[-1]["sourceName"] if images else "")


def start_recording(host: str) -> None:
    client(host).start_record()
    print("True")


def stop_recording(host: str) -> None:
    response = client(host).stop_record()
    output_path = getattr(response, "output_path", "")
    print(str(Path(output_path).resolve()) if output_path else "")


def check_recording(host: str) -> None:
    response = client(host).get_record_status()
    print("True" if response.output_active else "False")


def start_virtual_camera(host: str) -> None:
    c = client(host)
    if not c.get_virtual_cam_status().output_active:
        c.start_virtual_cam()
    print("True")


def stop_virtual_camera(host: str) -> None:
    client(host).stop_virtual_cam()
    print("False")


def virtual_camera_status(host: str) -> None:
    response = client(host).get_virtual_cam_status()
    print("True" if response.output_active else "False")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise ValueError("Missing OBS action")

    action = argv[1]
    host = argv[-1] if len(argv) > 2 else DEFAULT_HOST

    if action == "scene-list":
        scene_list(host)
    elif action == "switch":
        if len(argv) < 4:
            raise ValueError("switch requires <scene-name> <host>")
        switch(argv[2], argv[3])
    elif action == "active_scene_source":
        active_scene_source(host)
    elif action == "start_recording":
        start_recording(host)
    elif action == "stop_recording":
        stop_recording(host)
    elif action == "check_recording":
        check_recording(host)
    elif action == "start_virtual_camera":
        start_virtual_camera(host)
    elif action == "stop_virtual_camera":
        stop_virtual_camera(host)
    elif action == "virtual_camera_status":
        virtual_camera_status(host)
    else:
        raise ValueError("Unknown OBS action: %s" % action)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        print("OBS_ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
