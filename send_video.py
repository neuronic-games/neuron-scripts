#!/usr/bin/env python
"""Combine an intro, a recording, and an outro into one video and save it.

Usage:
    send_video.py <video_file> <number>

Builds:  {INTRO}\\{number}.mp4 + {video_file} + {OUTRO}\\{number}.mp4
Saves to: {OUTPUT}\\<YYYY-MM-DD-HH-MM>.flv

Requires ffmpeg. This script uses stream-copy (-c copy), which is fast but
requires the intro, recording, and outro to share the same codec,
resolution, and frame rate. FLV containers also only support H.264 (or a
few older codecs) for video and AAC/MP3 for audio, so if the source clips
use a different codec, ffmpeg will error on stream-copy and they'll need
to be re-encoded to a compatible codec first.

Folder paths and ffmpeg location come from settings.py: introDir, outroDir,
videoOutputDir, ffmpegPath.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import settings_loader  # must run before `import settings` below
import settings

INTRO_DIR = Path(settings.introDir)
OUTRO_DIR = Path(settings.outroDir)
OUTPUT_DIR = Path(settings.videoOutputDir)
FFMPEG_PATH = getattr(settings, "ffmpegPath", "ffmpeg")


def build_concat_file(list_path: Path, clips: list[Path]) -> None:
    lines = []
    for clip in clips:
        escaped = clip.as_posix().replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise ValueError("Usage: send_video.py <video_file> <number>")

    video = Path(argv[1]).resolve(strict=True)
    number = argv[2]
    if not int(number) > 0:
        raise ValueError("number must be positive")

    intro = (INTRO_DIR / f"{number}.mp4").resolve(strict=True)
    outro = (OUTRO_DIR / f"{number}.mp4").resolve(strict=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    output = OUTPUT_DIR / f"{timestamp}.flv"

    list_file = OUTPUT_DIR / f"_concat_{timestamp}.txt"
    build_concat_file(list_file, [intro, video, outro])

    try:
        subprocess.run(
            [
                FFMPEG_PATH,
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg failed: {exc.stderr}") from exc
    finally:
        list_file.unlink(missing_ok=True)

    print(str(output))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        print("SEND_ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
