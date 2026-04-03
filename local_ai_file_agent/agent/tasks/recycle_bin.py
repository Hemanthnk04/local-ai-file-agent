"""
RECYCLE_BIN — manage the agent's recycle bin.

The bin lives at BASE_DIR/.agent_bin/
Files deleted via batch_ops or moved here are recoverable.

Operations:
  list    → show bin contents
  restore → move a file back to its original location or a new location
  empty   → permanently delete everything in the bin
"""

import os
import shutil
import json
from datetime import datetime
from ..config import BASE_DIR, BIN_DIR, BIN_MAX_MB, BIN_MAX_ITEMS
from ..utils import confirm


# ── Manifest ──────────────────────────────────────────────────────────────────
MANIFEST_FILE = os.path.join(BIN_DIR, ".manifest.json")


def _load_manifest():
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_manifest(data):
    os.makedirs(BIN_DIR, exist_ok=True)
    with open(MANIFEST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def move_to_bin(original_path):
    """
    Move a file to the recycle bin.
    Records original path in manifest for restore.
    Returns (bin_path, error).
    """
    if not os.path.exists(original_path):
        return None, f"File not found: {original_path}"

    os.makedirs(BIN_DIR, exist_ok=True)

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = os.path.basename(original_path)
    bin_name = f"{ts}__{basename}"
    bin_path = os.path.join(BIN_DIR, bin_name)

    # Check bin limits before adding
    items = _list_bin()
    if len(items) >= BIN_MAX_ITEMS:
        return None, f"Bin is full ({BIN_MAX_ITEMS} items). Empty the bin first: type 'recycle bin'"
    current_mb = sum(os.path.getsize(f) for _, f, _ in items if os.path.exists(f)) // (1024*1024)
    if current_mb >= BIN_MAX_MB:
        return None, f"Bin exceeds {BIN_MAX_MB} MB. Empty the bin first: type 'recycle bin'"

    try:
        shutil.move(original_path, bin_path)
    except Exception as e:
        return None, str(e)

    # Update manifest
    manifest = _load_manifest()
    manifest[bin_name] = {
        "original_path": original_path,
        "deleted_at":    ts,
        "size":          os.path.getsize(bin_path),
    }
    _save_manifest(manifest)
    return bin_path, None


def _list_bin():
    """Return list of (bin_name, info_dict) from manifest + filesystem."""
    if not os.path.isdir(BIN_DIR):
        return []

    manifest = _load_manifest()
    items    = []

    for entry in sorted(os.listdir(BIN_DIR)):
        if entry == ".manifest.json":
            continue
        full = os.path.join(BIN_DIR, entry)
        if os.path.isfile(full):
            info = manifest.get(entry, {})
            items.append((entry, full, info))

    return items


def _format_size(n):
    if n < 1024:    return f"{n} B"
    if n < 1024**2: return f"{n//1024} KB"
    return f"{n//1024**2} MB"


# ── Entry point ───────────────────────────────────────────────────────────────

def run(filename=None, instructions=None, **kwargs):

    low = (instructions or "").lower()

    # Auto-detect operation
    if any(w in low for w in ("empty", "clear", "delete all", "wipe")):
        op = "empty"
    elif any(w in low for w in ("restore", "recover", "bring back", "undelete")):
        op = "restore"
    else:
        op = None

    if not op:
        print("\n  Recycle Bin operations:")
        print("    1. List bin contents")
        print("    2. Restore a file")
        print("    3. Empty bin (permanent delete)")
        choice = input("  Select: ").strip()
        op = {"1":"list","2":"restore","3":"empty"}.get(choice, "list")

    items = _list_bin()

    # ── LIST ──────────────────────────────────────────────────────────────
    if op == "list":
        if not items:
            print(f"\n  Recycle bin is empty.  ({BIN_DIR})")
            return
        print(f"\n  Recycle bin: {BIN_DIR}")
        print(f"  {'#':<4} {'Original path':<45} {'Deleted at':<18} {'Size':>8}")
        print(f"  {'─'*4} {'─'*45} {'─'*18} {'─'*8}")
        for i, (entry, full, info) in enumerate(items):
            orig = info.get("original_path", entry)
            ts   = info.get("deleted_at", "unknown")
            size = _format_size(info.get("size", os.path.getsize(full)))
            print(f"  [{i}] {orig:<45} {ts:<18} {size:>8}")
        return

    # ── RESTORE ───────────────────────────────────────────────────────────
    if op == "restore":
        if not items:
            print("  Recycle bin is empty.")
            return

        print(f"\n  Bin contents:")
        for i, (entry, full, info) in enumerate(items):
            orig = info.get("original_path", entry)
            print(f"    [{i}] {orig}")

        raw = input("  Enter number to restore: ").strip()
        try:
            idx         = int(raw)
            entry, full, info = items[idx]
        except (ValueError, IndexError):
            print("  Invalid selection.")
            return

        orig_path = info.get("original_path", "")
        dest      = input(f"  Restore to [{orig_path}]: ").strip() or orig_path

        if not dest:
            print("  No destination provided.")
            return

        if os.path.exists(dest):
            if not confirm(f"  '{dest}' already exists. Overwrite? (yes/no): "):
                return

        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        shutil.move(full, dest)

        # Remove from manifest
        manifest = _load_manifest()
        manifest.pop(entry, None)
        _save_manifest(manifest)

        print(f"  ✅ Restored: {dest}")
        return

    # ── EMPTY ─────────────────────────────────────────────────────────────
    if op == "empty":
        if not items:
            print("  Recycle bin is already empty.")
            return

        total = sum(os.path.getsize(f) for _, f, _ in items)
        print(f"\n  🛑 This will permanently delete {len(items)} item(s) ({_format_size(total)}).")
        print("  This cannot be undone.")

        if not confirm("  Empty bin? (yes/no): "):
            print("  Cancelled.")
            return

        for entry, full, _ in items:
            try:
                os.remove(full)
            except Exception as e:
                print(f"  ⚠  Could not delete '{entry}': {e}")

        # Clear manifest
        _save_manifest({})
        print(f"  ✅ Bin emptied — {len(items)} item(s) permanently deleted.")
