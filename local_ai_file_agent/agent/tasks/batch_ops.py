import os
import re
import shutil
from ..utils import confirm
from ..config import BASE_DIR
from .recycle_bin import move_to_bin


def _resolve_folder(filename, instructions):
    """Try to find a folder from classifier output or instructions."""

    # 1. filename field from classifier
    if filename:
        candidate = filename.strip()
        if os.path.isdir(candidate):
            return candidate
        # try relative
        rel = os.path.join(BASE_DIR, candidate)
        if os.path.isdir(rel):
            return rel

    # 2. parse instructions for a path
    if instructions:
        # Windows absolute path
        win = re.search(r"[A-Za-z]:[/\\][^\s,]+", instructions)
        if win:
            p = win.group(0).rstrip(".,")
            if os.path.isdir(p):
                return p
        # Unix-style or relative path token that exists
        tokens = re.findall(r"[A-Za-z0-9_./ \\-]+", instructions)
        for t in tokens:
            t = t.strip()
            if os.path.isdir(t):
                return t
            rel = os.path.join(BASE_DIR, t)
            if os.path.isdir(rel):
                return rel

    return None


def _detect_operation(instructions):
    """Guess the intended sub-operation from the instruction text."""
    if not instructions:
        return None
    low = instructions.lower()
    if any(w in low for w in ("rename", "name")):
        return "1"
    if any(w in low for w in ("delete", "remove", "erase")):
        return "2"
    if any(w in low for w in ("move", "transfer", "copy")):
        return "3"
    return None


def _list_entries(folder):
    try:
        entries = sorted(os.listdir(folder))
    except FileNotFoundError:
        return []
    return [e for e in entries if not e.startswith(".")]


def _pick_files(folder):
    """Interactive file picker."""
    entries = _list_entries(folder)

    if not entries:
        print("  No files found in folder.")
        return []

    print(f"\n  Contents of: {folder}\n")
    for i, name in enumerate(entries):
        full = os.path.join(folder, name)
        kind = "[DIR] " if os.path.isdir(full) else "[FILE]"
        print(f"    [{i}] {kind} {name}")

    print("\n  Enter numbers to select (comma-separated), or press Enter for ALL:")
    raw = input("  > ").strip()

    if not raw:
        return [os.path.join(folder, e) for e in entries]

    try:
        indices = [int(x.strip()) for x in raw.split(",")]
        return [os.path.join(folder, entries[i]) for i in indices if 0 <= i < len(entries)]
    except ValueError:
        print("  Invalid selection.")
        return []


# ──────────────────────────────────────────────
# SUB-OPERATIONS
# ──────────────────────────────────────────────

def batch_rename(folder, instructions=None):
    """Rename files via find-and-replace on the filename."""

    # Try to extract find/replace from instructions
    find_hint = replace_hint = ""
    if instructions:
        m = re.search(r"(?:rename|replace)[^\"']*[\"']([^\"']+)[\"'][^\"']*[\"']([^\"']+)[\"']", instructions, re.I)
        if m:
            find_hint, replace_hint = m.group(1), m.group(2)

    files = _pick_files(folder)
    if not files:
        return

    find = find_hint or input("\n  Find text in filename: ").strip()
    if not find:
        print("  Nothing to find.")
        return
    replace = replace_hint or input("  Replace with: ").strip()

    plan = []
    for path in files:
        if os.path.isdir(path):
            continue
        name = os.path.basename(path)
        if find in name:
            new_name = name.replace(find, replace)
            new_path = os.path.join(os.path.dirname(path), new_name)
            plan.append((path, new_path))

    if not plan:
        print(f"  No filenames contain '{find}'.")
        return

    print("\n  Rename plan:")
    for old, new in plan:
        print(f"    {os.path.basename(old)}  →  {os.path.basename(new)}")

    if not confirm("\n  Apply renames? (yes/no): "):
        print("  Cancelled.")
        return

    for old, new in plan:
        if os.path.exists(new):
            print(f"  ⚠  Target already exists, skipping: {os.path.basename(new)}")
            continue
        os.rename(old, new)
        print(f"  ✅ Renamed: {os.path.basename(new)}")


def batch_delete(folder, instructions=None):
    """Delete selected files with double confirmation."""

    files = _pick_files(folder)
    if not files:
        return

    print("\n  🛑 Selected for deletion:")
    for f in files:
        print(f"    {f}")

    print(f"\n  This will permanently delete {len(files)} item(s).")

    if not confirm("  Are you sure? (yes/no): "):
        print("  Cancelled.")
        return

    # Second confirmation for bulk delete
    if len(files) > 3:
        if not confirm(f"  Final confirm — delete all {len(files)} items? (yes/no): "):
            print("  Cancelled.")
            return

    for f in files:
        try:
            # Move to recycle bin instead of permanent delete
            bin_path, err = move_to_bin(f)
            if err:
                print(f"  ❌ Could not move to bin: {err}")
                continue
            print(f"  ✅ Moved to bin: {f}")
            print(f"  💾 Bin path   : {bin_path}")
        except Exception as e:
            print(f"  ❌ Error deleting '{f}': {e}")


def batch_move(folder, instructions=None):
    """Move selected files to a destination folder."""

    files = _pick_files(folder)
    if not files:
        return

    # Try to extract destination from instructions
    dest = ""
    if instructions:
        m = re.search(r"(?:to|into|destination)[:\s]+([A-Za-z0-9_.:/\\-]+)", instructions, re.I)
        if m:
            candidate = m.group(1).strip()
            if os.path.isdir(candidate):
                dest = candidate

    dest = dest or input("\n  Destination folder: ").strip()

    if not dest:
        print("  No destination provided.")
        return

    if not os.path.exists(dest):
        if confirm(f"  Folder '{dest}' does not exist. Create it? (yes/no): "):
            os.makedirs(dest, exist_ok=True)
        else:
            print("  Cancelled.")
            return

    print("\n  Move plan:")
    for f in files:
        print(f"    {f}  →  {os.path.join(dest, os.path.basename(f))}")

    if not confirm("\n  Apply moves? (yes/no): "):
        print("  Cancelled.")
        return

    for f in files:
        try:
            target = os.path.join(dest, os.path.basename(f))
            if os.path.exists(target):
                print(f"  ⚠  Already exists at destination, skipping: {os.path.basename(f)}")
                continue
            shutil.move(f, target)
            print(f"  ✅ Moved: {os.path.basename(f)}")
        except Exception as e:
            print(f"  ❌ Error moving '{f}': {e}")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

OPERATIONS = {
    "1": ("Rename files", batch_rename),
    "2": ("Delete files", batch_delete),
    "3": ("Move files",   batch_move),
}


def run(filename=None, instructions=None, **kwargs):

    folder = _resolve_folder(filename, instructions)

    if not folder:
        folder = input("  Enter folder path (leave empty for current directory): ").strip()
        if not folder:
            folder = os.getcwd()

    if not os.path.isdir(folder):
        print(f"  Folder not found: {folder}")
        return

    print(f"\n  Working folder: {folder}")

    # Try to auto-detect operation from instructions
    auto = _detect_operation(instructions)

    if auto:
        label, fn = OPERATIONS[auto]
        print(f"  Operation: {label}")
        fn(folder, instructions)
        return

    print("\n  Batch operations:")
    for key, (label, _) in OPERATIONS.items():
        print(f"    {key}. {label}")

    choice = input("\n  Select operation: ").strip()

    if choice not in OPERATIONS:
        print("  Invalid choice.")
        return

    _, fn = OPERATIONS[choice]
    fn(folder, instructions)
