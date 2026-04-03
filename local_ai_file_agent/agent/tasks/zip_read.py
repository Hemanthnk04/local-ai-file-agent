"""
ZIP_READ — inspect, extract, and work with ZIP archives.

Operations:
  list     → show contents with sizes
  extract  → extract all or selected files
  read     → read a specific file inside the zip without extracting
  extract_to_bin → extract to recycle bin (safe temporary extraction)
"""

import os
import re
from ..config import BIN_DIR
from ..resolve import resolve_single
from ..utils import confirm
from ..guardrails import run_write_guardrails


def _format_size(n):
    if n < 1024:        return f"{n} B"
    if n < 1024**2:     return f"{n//1024} KB"
    return f"{n//1024**2} MB"


def _list_zip(zf):
    """Print a formatted table of zip contents."""
    infos = zf.infolist()
    print(f"\n  {'Name':<45} {'Compressed':>12} {'Original':>12}")
    print(f"  {'─'*45} {'─'*12} {'─'*12}")
    for info in infos:
        is_dir   = info.filename.endswith("/")
        icon     = "📁" if is_dir else "📄"
        comp     = _format_size(info.compress_size)
        orig     = _format_size(info.file_size)
        print(f"  {icon} {info.filename:<43} {comp:>12} {orig:>12}")
    total_orig = sum(i.file_size for i in infos)
    print(f"\n  {len(infos)} item(s) — total uncompressed: {_format_size(total_orig)}")
    return infos


def _pick_files_from_zip(infos):
    """Let user select specific files from a zip."""
    files = [i for i in infos if not i.filename.endswith("/")]
    if not files:
        return []

    print("\n  Files in archive:")
    for i, info in enumerate(files):
        print(f"    [{i}] {info.filename}  ({_format_size(info.file_size)})")

    raw = input("  Select numbers (comma-separated, Enter = all): ").strip()
    if not raw:
        return files

    try:
        indices = [int(x.strip()) for x in raw.split(",")]
        return [files[i] for i in indices if 0 <= i < len(files)]
    except ValueError:
        return files


def _detect_operation(instructions):
    """Guess operation from instruction text."""
    if not instructions:
        return None
    low = instructions.lower()
    if any(w in low for w in ("list", "show", "contents", "what's inside", "inspect")):
        return "list"
    if any(w in low for w in ("read", "view", "print", "display", "open")):
        return "read"
    if any(w in low for w in ("extract", "unzip", "decompress")):
        return "extract"
    return None


def _read_file_in_zip(zf, infos, instructions):
    """Read a specific file inside the zip and print its contents."""
    # Try to detect filename from instructions
    target = None
    if instructions:
        m = re.search(r'[\w./\\-]+\.[\w]+', instructions)
        if m:
            candidate = m.group(0).strip()
            # Find in zip
            for info in infos:
                if os.path.basename(info.filename).lower() == candidate.lower():
                    target = info
                    break

    if not target:
        files = [i for i in infos if not i.filename.endswith("/")]
        if len(files) == 1:
            target = files[0]
        else:
            print("\n  Which file do you want to read?")
            for i, info in enumerate([i for i in infos if not i.filename.endswith("/")]):
                print(f"    [{i}] {info.filename}")
            raw = input("  Enter number: ").strip()
            try:
                files = [i for i in infos if not i.filename.endswith("/")]
                target = files[int(raw)]
            except (ValueError, IndexError):
                print("  Invalid selection.")
                return

    try:
        content = zf.read(target.filename).decode("utf-8", errors="replace")
        print(f"\n  {'─'*52}")
        print(f"  FILE: {target.filename}  ({_format_size(target.file_size)})")
        print(f"  {'─'*52}\n")
        print(content[:8000])
        if len(content) > 8000:
            print(f"\n  ... [{len(content)-8000:,} more chars truncated]")
    except Exception as e:
        print(f"  ❌ Cannot read '{target.filename}': {e}")


def _extract_zip(zf, infos, dest_dir, to_bin=False):
    """Extract selected files to dest_dir."""
    selected = _pick_files_from_zip(infos)
    if not selected:
        print("  Nothing to extract.")
        return

    os.makedirs(dest_dir, exist_ok=True)

    label = "bin" if to_bin else dest_dir
    print(f"\n  Extracting {len(selected)} file(s) → {label}")

    for info in selected:
        ok, reason = run_write_guardrails(info.filename)
        if not ok:
            print(f"  ⚠  Skipping '{info.filename}': {reason}")
            continue
        try:
            zf.extract(info, dest_dir)
            print(f"  ✅ {info.filename}")
        except Exception as e:
            print(f"  ❌ {info.filename}: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

OPERATIONS = {
    "1": "List contents",
    "2": "Read a file inside the zip",
    "3": "Extract to folder",
    "4": "Extract to recycle bin (temporary)",
}


def run(filename=None, instructions=None, **kwargs):
    import zipfile

    # Resolve zip file
    path = resolve_single(filename, instructions, prompt_label="ZIP file")
    if not path:
        print("  No ZIP file specified.")
        return

    if not path.lower().endswith(".zip"):
        print(f"  ⚠  '{path}' does not appear to be a ZIP file.")
        if not confirm("  Continue anyway? (yes/no): "):
            return

    if not zipfile.is_zipfile(path):
        print(f"  ❌ '{path}' is not a valid ZIP file.")
        return

    print(f"\n  Archive: {path}")
    print(f"  Size   : {_format_size(os.path.getsize(path))}")

    # Auto-detect operation
    op = _detect_operation(instructions)

    if not op:
        print("\n  Operations:")
        for k, v in OPERATIONS.items():
            print(f"    {k}. {v}")
        op_choice = input("\n  Select operation: ").strip()
        op = {"1":"list","2":"read","3":"extract","4":"bin"}.get(op_choice)
        if not op:
            print("  Invalid choice.")
            return

    with zipfile.ZipFile(path, "r") as zf:
        infos = zf.infolist()

        if op == "list":
            _list_zip(zf)

        elif op == "read":
            _list_zip(zf)
            _read_file_in_zip(zf, infos, instructions)

        elif op == "extract":
            _list_zip(zf)
            default_dest = os.path.join(os.path.dirname(path),
                                        os.path.splitext(os.path.basename(path))[0])
            dest = input(f"  Extract to [{default_dest}]: ").strip() or default_dest
            if not confirm(f"  Extract to '{dest}'? (yes/no): "):
                return
            _extract_zip(zf, infos, dest)
            print(f"\n  ✅ Extraction complete → {dest}")

        elif op == "bin":
            _list_zip(zf)
            dest = os.path.join(BIN_DIR, os.path.splitext(os.path.basename(path))[0])
            print(f"  Extracting to bin: {dest}")
            _extract_zip(zf, infos, dest, to_bin=True)
            print(f"\n  ✅ Extracted to recycle bin → {dest}")
            print(f"     Use 'restore from bin' or browse: {BIN_DIR}")
