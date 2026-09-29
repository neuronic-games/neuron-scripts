#!/usr/bin/env python
"""Delete files in a folder older than a cutoff age.

Usage (one-shot):
    clean_up_folder.py <folder> [age] [--unit days|hours|minutes] [--pattern GLOB] [--recursive] [--dry-run]

Usage (background loop, entirely settings.py-driven):
    clean_up_folder.py --loop

Age is based on each file's last-modified time. Only files directly in
<folder> are considered by default - subfolders are left alone entirely
(not walked into, never deleted themselves). Pass --recursive to also
walk into subfolders (their contents can be deleted; the subfolders
themselves still never are).

age defaults to settings.cleanupMaxAgeDays (1 if that isn't set in
settings.py) - pass a number on the command line to override it for a
single run without touching settings.py. --unit picks what that number
(and settings.cleanupMaxAgeDays) is measured in - days (the default),
hours, or minutes.

--loop mode ignores <folder>/age/--unit/etc. entirely and instead reads
settings.cleanupFolders (a list of folders to watch, each with its own
age/unit/pattern/recursive) and settings.cleanupIntervalSec (how often to
recheck), looping forever - see settings.py.sample for the exact format.
It still no-ops (prints a message and exits immediately) if run with
cleanupFolders empty, but launch.cmd/launch.sh check that setting
themselves first and only start this at all when it's non-empty.

Examples:
    python clean_up_folder.py "C:\\...\\recordings"
    python clean_up_folder.py "C:\\...\\recordings" 7
    python clean_up_folder.py "C:\\...\\recordings" 6 --unit hours
    python clean_up_folder.py "C:\\...\\recordings" 30 --unit minutes
    python clean_up_folder.py "C:\\...\\output" --pattern "*.mp4" --dry-run
    python clean_up_folder.py --loop
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import settings_loader  # must run before `import settings` below
import settings

DEFAULT_MAX_AGE_DAYS = getattr(settings, "cleanupMaxAgeDays", 1)

# Seconds per unit, for converting the age value (whatever unit it's given
# in) into a cutoff timestamp.
_UNIT_SECONDS = {
    "days": 86400,
    "hours": 3600,
    "minutes": 60,
}


def find_old_files(folder: Path, max_age: float, unit: str, pattern: str, recursive: bool) -> Iterator[Path]:
    cutoff = time.time() - (max_age * _UNIT_SECONDS[unit])
    glob_fn = folder.rglob if recursive else folder.glob
    for path in glob_fn(pattern):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                yield path
        except OSError:
            continue


def clean_folder(
    folder: Path, max_age: float, unit: str, pattern: str, recursive: bool, dry_run: bool
) -> tuple[int, int, int]:
    """Delete (or list, if dry_run) files in `folder` older than max_age
    `unit`(s). Returns (deleted_count, freed_bytes, error_count). Shared by
    both the one-shot CLI path and the --loop path, so both behave/print
    identically for a single folder."""
    deleted_count = 0
    freed_bytes = 0
    error_count = 0

    for path in find_old_files(folder, max_age, unit, pattern, recursive):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        if dry_run:
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

    verb = "Would delete" if dry_run else "Deleted"
    unit_label = unit[:-1] if max_age == 1 else unit  # "1 day" vs "2 days"
    print(
        f"{verb} {deleted_count} file(s), {freed_bytes / (1024 ** 2):.1f} MB, "
        f"older than {max_age} {unit_label} in {folder}"
        + (f" ({error_count} error(s))" if error_count else "")
    )

    return deleted_count, freed_bytes, error_count


def _normalize_loop_entries(raw_entries: list[Any]) -> list[dict]:
    """Turn settings.cleanupFolders entries (each either a plain folder
    path string, or a dict overriding any of maxAge/unit/pattern/recursive)
    into fully-specified dicts, falling back to settings.cleanupMaxAgeDays/
    "days"/"*"/False for anything not overridden."""
    entries = []
    for raw in raw_entries:
        if isinstance(raw, str):
            raw = {"folder": raw}
        folder = raw.get("folder")
        if not folder:
            print(f"Skipping cleanupFolders entry with no 'folder': {raw!r}", file=sys.stderr)
            continue
        entries.append({
            "folder": Path(folder),
            "max_age": raw.get("maxAge", DEFAULT_MAX_AGE_DAYS),
            "unit": raw.get("unit", "days"),
            "pattern": raw.get("pattern", "*"),
            "recursive": raw.get("recursive", False),
        })
    return entries


def run_loop() -> int:
    """Reread nothing from the CLI - entirely settings.py-driven (see
    module docstring). Runs forever, one pass over every cleanupFolders
    entry every cleanupIntervalSec seconds, until interrupted."""
    raw_entries = getattr(settings, "cleanupFolders", [])
    if not raw_entries:
        print("settings.cleanupFolders is empty - nothing to do.")
        return 0

    entries = _normalize_loop_entries(raw_entries)
    interval_sec = float(getattr(settings, "cleanupIntervalSec", 60))

    print(f"clean_up_folder.py --loop starting: {len(entries)} folder(s), checking every {interval_sec}s")
    for entry in entries:
        print(f"  {entry['folder']}: older than {entry['max_age']} {entry['unit']} (pattern={entry['pattern']!r}, recursive={entry['recursive']})")

    try:
        while True:
            for entry in entries:
                folder = entry["folder"]
                if not folder.is_dir():
                    print(f"Not a folder, skipping this pass: {folder}", file=sys.stderr)
                    continue
                try:
                    clean_folder(
                        folder, entry["max_age"], entry["unit"], entry["pattern"], entry["recursive"], dry_run=False,
                    )
                except Exception as e:
                    print(f"Error cleaning up {folder}: {e}", file=sys.stderr)
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        print("Stopping.")
        return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Delete files in a folder older than a cutoff age.")
    parser.add_argument(
        "--loop", action="store_true",
        help="Ignore all other arguments and run forever, cleaning up settings.cleanupFolders "
             "every settings.cleanupIntervalSec seconds (see module docstring)",
    )
    parser.add_argument("folder", nargs="?", help="Folder to clean up (not used with --loop)")
    parser.add_argument(
        "age", nargs="?", type=float, default=None,
        help=f"Delete files older than this (default: settings.cleanupMaxAgeDays = {DEFAULT_MAX_AGE_DAYS}, unit set by --unit)",
    )
    parser.add_argument(
        "--unit", choices=sorted(_UNIT_SECONDS), default="days",
        help="Unit that 'age' (and settings.cleanupMaxAgeDays) is measured in (default: days)",
    )
    parser.add_argument("--pattern", default="*", help="Only match files against this glob pattern (default: * = all files)")
    parser.add_argument("--recursive", action="store_true", help="Also walk into subfolders (subfolders themselves are never deleted)")
    parser.add_argument("--dry-run", action="store_true", help="List what would be deleted without deleting anything")
    args = parser.parse_args(argv[1:])

    if args.loop:
        return run_loop()

    if not args.folder:
        parser.error("folder is required unless --loop is given")

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Not a folder: {folder}", file=sys.stderr)
        return 1

    max_age = args.age if args.age is not None else DEFAULT_MAX_AGE_DAYS
    unit = args.unit

    _, _, error_count = clean_folder(folder, max_age, unit, args.pattern, args.recursive, args.dry_run)

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
