#!/usr/bin/env python
"""Continuously publish lightweight OBS Program Preview JPEG frames for AIR."""

from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

from obsws_python import ReqClient


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise ValueError("Usage: obs_preview.py <host> <output-file>")

    host = argv[1] or "127.0.0.1"
    output = Path(argv[2])
    temporary = output.with_suffix(output.suffix + ".tmp")
    output.parent.mkdir(parents=True, exist_ok=True)
    client = ReqClient(host=host, port=4455, password="", timeout=5)

    while True:
        scene = client.get_current_program_scene().scene_name
        response = client.get_source_screenshot(scene, "jpg", 640, 360, 75)
        image_data = response.image_data.split(",", 1)[-1]
        temporary.write_bytes(base64.b64decode(image_data))
        os.replace(temporary, output)
        time.sleep(0.2)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as exc:
        print("OBS_PREVIEW_ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
