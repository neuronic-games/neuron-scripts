#!/usr/bin/env python
"""Delete files in a folder older than a cutoff age.

Usage:
    clean_up_folder.py <folder> [days] [--pattern GLOB] [--recursive] [--dry-run]

Age is based on each file's last-modified time. Only files directly in
<folder> are considered by default - subfolders are left alone entirely
(not walked into, never deleted themselves). Pass --recursive to also
walk into subfolders (their contents can be deleted; the subfolders
themselves still never are).

days defaults to settings.cleanupMaxAgeDays (1 if that isn't set in
settings.py) - pass a number on the command line to override it for a
single run without touching settings.py.

Examples:
    python clean_up_folder.py "C:\\...\\recordings"
    python clean_up_folder.py "C:\\...\\recordings" 7
    python clean_up_folder.py "C:\\...\\output" --pattern "*.mp4" --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Iterator

import settings_loader  # must run before `import settings` below
import settings

DEFAULT_MAX_AGE_DAYS = getattr(settings, "cleanupMaxAgeDays", 1)


def find_old_files(folder: Path, max_age_days: float, pattern: str, recursive: bool) -> Iterator[Path]:
    cutoff = time.time() - (max_age_days * 86400)
    glob_fn = folder.rglob if recursive else folder.glob
    for path in glob_fn(pattern):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                yield path
        except OSError:
            continue


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Delete files in a folder older than a cutoff age.")
    parser.add_argument("folder", help="Folder to clean up")
    parser.add_argument(
        "days", nargs="?", type=float, default=None,
        help=f"Delete files older than this many days (default: settings.cleanupMaxAgeDays = {DEFAULT_MAX_AGE_DAYS})",
    )
    parser.add_argument("--pattern", default="*", help="Only match files against this glob pattern (default: * = all files)")
    parser.add_argument("--recursive", action="store_true", help="Also walk into subfolders (subfolders themselves are never deleted)")
    parser.add_argument("--dry-run", action="store_true", help="List what would be deleted without deleting anything")
    args = parser.parse_args(argv[1:])

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Not a folder: {folder}", file=sys.stderr)
        return 1

    max_age_days = args.days if args.days is not None else DEFAULT_MAX_AGE_DAYS

    deleted_count = 0
    freed_bytes = 0
    error_count = 0

    for path in find_old_files(folder, max_age_days, args.pattern, args.recursive):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        if args.dry_run:
            print(f"Would delete: {path} ({size} bytes)")
            deleted_count += 1
            freed_bytes += size
            continue

        try:
            path.unlink()
            print(f"Deleted: {path} ({size} bytes)")
            deleted_count += 1
            freed_bytes += size
        except OSError as e:
            print(f"Could not delete {path}: {e}", file=sys.stderr)
            error_count += 1

    verb = "Would delete" if args.dry_run else "Deleted"
    print(
        f"{verb} {deleted_count} file(s), {freed_bytes / (1024 ** 2):.1f} MB, "
        f"older than {max_age_days} day(s) in {folder}"
        + (f" ({error_count} error(s))" if error_count else "")
    )

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
