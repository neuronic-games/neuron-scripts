#!/usr/bin/env python
"""Combine an intro, a recording, and an outro into one video and save it.

Usage:
    send_video.py <video_file> <number>

Builds:  {INTRO}\\{number}.mp4 + {video_file} + {OUTRO}\\{number}.mp4
Saves to: {OUTPUT}\\<YYYY-MM-DD-HH-MM>.mp4

Requires ffmpeg. Re-encodes (H.264/AAC) rather than stream-copying, so the
intro/recording/outro don't need matching codecs, resolution, or frame
rate, and the output doesn't inherit any keyframe/timestamp mismatches at
the clip boundaries that stream-copy concat is prone to (this was
previously -c copy, which is faster but produced files that played back
broken/hung in some players when the source clips weren't
frame-for-frame identical in encoding). -movflags +faststart also moves
the MP4 index to the front of the file for reliable playback start.

Folder paths and ffmpeg location come from settings.py: introDir, outroDir,
videoOutputDir, ffmpegPath.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import settings_loader  # must run before `import settings` below
import settings

INTRO_DIR = Path(settings.introDir)
OUTRO_DIR = Path(settings.outroDir)
OUTPUT_DIR = Path(settings.videoOutputDir)
FFMPEG_PATH = getattr(settings, "ffmpegPath", "ffmpeg")
TARGET_WIDTH = int(getattr(settings, "videoTargetWidth", 1280))
TARGET_HEIGHT = int(getattr(settings, "videoTargetHeight", 720))
TARGET_FPS = int(getattr(settings, "videoTargetFps", 30))


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
    # Not strict=True: unlike intro/video/outro, this file doesn't exist yet
    # - it's the one we're about to create.
    output = (OUTPUT_DIR / f"{timestamp}.mp4").resolve()

    # concat *filter* (not the -f concat demuxer) - this decodes each clip
    # independently before joining them, so intro/recording/outro can have
    # different codecs, resolutions, or frame rates. The demuxer approach
    # only works when every input already shares the same codec; mixing
    # codecs through it produces corrupt/unplayable output even with
    # re-encoding enabled, since it works at the raw byte/packet level
    # rather than decoding first.
    #
    # The concat filter itself still requires every video input to already
    # be the same frame size/rate, so each clip is first scaled to fit
    # within TARGET_WIDTH x TARGET_HEIGHT (letterboxed with black bars,
    # never stretched/cropped) and normalized to TARGET_FPS, and each
    # audio track is resampled to a common format, before joining. Each
    # clip needs both a video and an audio stream (v=1:a=1) - a silent
    # intro/outro still needs a (silent) audio track.
    per_clip_filters = []
    concat_inputs = []
    for i in range(3):
        per_clip_filters.append(
            f"[{i}:v:0]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps={TARGET_FPS}[v{i}]"
        )
        per_clip_filters.append(
            f"[{i}:a:0]aformat=sample_rates=44100:channel_layouts=stereo[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    filter_complex = ";".join(per_clip_filters)
    filter_complex += f";{''.join(concat_inputs)}concat=n=3:v=1:a=1[outv][outa]"

    # Render to a temp file first, then move the finished file into
    # videoOutputDir as a last step. ffmpeg takes several seconds to
    # re-encode - writing straight to `output` would mean anything watching
    # videoOutputDir (or a viewer opening the file early) could see a
    # partially-written file sitting under its final name and mistake it
    # for a finished (but broken/truncated) video. Rendering elsewhere and
    # only placing the file at `output` once ffmpeg has fully succeeded
    # avoids that window - the file only ever appears in videoOutputDir
    # once it's complete.
    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".mp4", prefix="send_video_")
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)

    try:
        try:
            subprocess.run(
                [
                    FFMPEG_PATH,
                    "-y",  # overwrite the empty placeholder mkstemp() created
                    "-i", str(intro),
                    "-i", str(video),
                    "-i", str(outro),
                    "-filter_complex", filter_complex,
                    "-map", "[outv]",
                    "-map", "[outa]",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "18",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    str(tmp_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"ffmpeg failed: {exc.stderr}") from exc

        # shutil.move (not os.replace) since the system temp dir and
        # videoOutputDir may be on different drives/filesystems - move()
        # falls back to a copy+delete in that case, os.replace() would just
        # raise.
        shutil.move(str(tmp_path), str(output))
    finally:
        # Only still present if we raised before the move above succeeded.
        tmp_path.unlink(missing_ok=True)

    print(str(output))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        print("SEND_ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
