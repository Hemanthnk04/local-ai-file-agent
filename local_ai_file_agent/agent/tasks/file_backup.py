"""
FILE_BACKUP — copy a file or folder to a timestamped backup location.
Called automatically by rewrite_file and batch_ops (delete) before any
destructive operation, and also available as a standalone task.
"""

import os
import shutil
from datetime import datetime
from ..config import BASE_DIR


def _backup_path(original_path):
    """Return a timestamped backup path next to the original."""
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_  = os.path.dirname(original_path) or BASE_DIR
    base  = os.path.basename(original_path)
    name, ext = os.path.splitext(base)
    return os.path.join(dir_, f"{name}.backup_{ts}{ext}")


def backup(original_path):
    """
    Create a backup of a file or folder.
    Returns (backup_path, error_string).
    On success error_string is None.
    """
    if not os.path.exists(original_path):
        return None, f"Cannot back up — path not found: {original_path}"

    dest = _backup_path(original_path)

    try:
        if os.path.isdir(original_path):
            shutil.copytree(original_path, dest)
        else:
            shutil.copy2(original_path, dest)
        return dest, None
    except Exception as e:
        return None, str(e)


def backup_silently(original_path):
    """
    Back up without printing anything on success.
    Prints a warning on failure. Returns backup path or None.
    """
    dest, err = backup(original_path)
    if err:
        print(f"  ⚠  Backup failed for '{original_path}': {err}")
        return None
    return dest


# ── Standalone task entry point ───────────────────────────────────────────────

def run(filename=None, instructions=None, **kwargs):
    from ..resolve import resolve_single

    path = resolve_single(filename, instructions, prompt_label="file or folder to back up")

    if not path:
        print("  No file specified.")
        return

    print(f"  Backing up: {path}")
    dest, err = backup(path)

    if err:
        print(f"  ❌ {err}")
    else:
        print(f"  ✅ Backup saved: {dest}")
