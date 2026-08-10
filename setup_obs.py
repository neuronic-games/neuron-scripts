#!/usr/bin/env python
"""Create the local OBS scene/profile expected by the LICM recorder."""

from __future__ import annotations

import os
from pathlib import Path

from obsws_python import ReqClient


HOST = os.getenv("OBS_HOST", "127.0.0.1")
PORT = int(os.getenv("OBS_PORT", "4455"))
PASSWORD = os.getenv("OBS_PASSWORD", "")
CAMERA_NAME = os.getenv("OBS_CAMERA_SOURCE", "Integrated Webcam")
BACKGROUND_REMOVAL_FILTER = "AI Background Removal"
RECORDINGS = Path.home() / "Documents" / "Neuronic" / "hpcm-tv-record" / "recordings"
BACKGROUNDS = Path.home() / "Documents" / "Neuronic" / "hpcm-tv-record" / "background"


def main() -> None:
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    c = ReqClient(host=HOST, port=PORT, password=PASSWORD, timeout=5)

    scenes = {item["sceneName"] for item in c.get_scene_list().scenes}
    inputs = {item["inputName"] for item in c.get_input_list().inputs}

    for story_id in range(1, 9):
        scene_name = "Story %d" % story_id
        background_name = "%s Background" % scene_name
        background_path = BACKGROUNDS / ("%d.png" % story_id)

        if scene_name not in scenes:
            c.create_scene(scene_name)
            scenes.add(scene_name)

        scene_items = c.get_scene_item_list(scene_name).scene_items
        item_names = {item["sourceName"] for item in scene_items}

        if background_name not in inputs:
            response = c.create_input(
                scene_name,
                background_name,
                "image_source",
                {"file": str(background_path)},
                True,
            )
            background_item_id = response.scene_item_id
            inputs.add(background_name)
        else:
            c.set_input_settings(background_name, {"file": str(background_path)}, True)
            if background_name not in item_names:
                background_item_id = c.create_scene_item(scene_name, background_name, True).scene_item_id
            else:
                background_item_id = next(
                    item["sceneItemId"] for item in scene_items if item["sourceName"] == background_name
                )

        c.set_scene_item_transform(
            scene_name,
            background_item_id,
            {"boundsType": "OBS_BOUNDS_STRETCH", "boundsWidth": 1280, "boundsHeight": 720},
        )
        c.set_scene_item_index(scene_name, background_item_id, 0)

        if CAMERA_NAME not in inputs:
            camera_item_id = c.create_input(scene_name, CAMERA_NAME, "dshow_input", {}, True).scene_item_id
            inputs.add(CAMERA_NAME)
        elif CAMERA_NAME not in item_names:
            camera_item_id = c.create_scene_item(scene_name, CAMERA_NAME, True).scene_item_id
        else:
            camera_item_id = next(
                item["sceneItemId"] for item in scene_items if item["sourceName"] == CAMERA_NAME
            )

        c.set_scene_item_transform(
            scene_name,
            camera_item_id,
            {"boundsType": "OBS_BOUNDS_STRETCH", "boundsWidth": 1280, "boundsHeight": 720},
        )
        c.set_scene_item_index(scene_name, camera_item_id, 1)

    filter_kinds = set(c.get_source_filter_kind_list().source_filter_kinds)
    if "background_removal" in filter_kinds:
        filters = c.get_source_filter_list(CAMERA_NAME).filters
        if not any(item["filterName"] == BACKGROUND_REMOVAL_FILTER for item in filters):
            c.create_source_filter(
                CAMERA_NAME,
                BACKGROUND_REMOVAL_FILTER,
                "background_removal",
                {
                    "model_select": "models/mediapipe.with_runtime_opt.ort",
                    "useGPU": "cpu",
                    "enable_threshold": True,
                    "threshold": 0.5,
                    "smooth_contour": 0.5,
                    "temporal_smooth_factor": 0.85,
                    "mask_every_x_frames": 1,
                    "stop_when_source_is_inactive": False,
                    "disabled": False,
                },
            )
    else:
        print("Warning: OBS background-removal plugin is not installed; camera will cover the background.")

    c.set_current_program_scene("Story 1")
    if not c.get_virtual_cam_status().output_active and not c.get_record_status().output_active:
        c.set_video_settings(30, 1, 1280, 720, 1280, 720)
    c.set_profile_parameter("Output", "Mode", "Simple")
    c.set_profile_parameter("SimpleOutput", "FilePath", str(RECORDINGS))
    c.set_profile_parameter("SimpleOutput", "RecFormat2", "mp4")
    c.set_profile_parameter("SimpleOutput", "VRecEncoder", "obs_qsv11_v2")
    print("OBS scenes/profile ready: Story 1 through Story 8")


if __name__ == "__main__":
    main()
