"""
ZIP_CREATE — create ZIP archives.

Two modes:
  folder  → compress an existing folder into a .zip
  files   → generate files via LLM (using CREATE_FILE logic) then pack into a .zip

Also supports: add existing files to a new zip, or zip a list of named files.
"""

import os
import re
from ..config import BASE_DIR
from ..resolve import resolve_multi
from ..utils import confirm
from ..guardrails import run_write_guardrails


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_size(n):
    if n < 1024:        return f"{n} B"
    if n < 1024**2:     return f"{n//1024} KB"
    return f"{n//1024**2} MB"


def _zip_folder(folder_path, out_zip, exclude_dirs=None):
    import zipfile
    """
    Compress an entire folder into a zip.
    Returns (file_count, total_size).
    """
    exclude_dirs = exclude_dirs or {"__pycache__", ".git", "node_modules", ".agent_bin"}
    file_count   = 0
    total_size   = 0

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, os.path.dirname(folder_path))
                zf.write(full, arcname)
                file_count += 1
                total_size += os.path.getsize(full)

    return file_count, total_size


def _zip_files(file_paths, out_zip, base_dir=None):
    import zipfile
    """
    Zip a list of specific files.
    Returns (file_count, total_size).
    """
    base_dir   = base_dir or BASE_DIR
    file_count = 0
    total_size = 0

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in file_paths:
            if not os.path.isfile(path):
                print(f"  ⚠  Skipping (not found): {path}")
                continue
            try:
                arcname = os.path.relpath(path, base_dir)
            except ValueError:
                arcname = os.path.basename(path)
            zf.write(path, arcname)
            file_count += 1
            total_size += os.path.getsize(path)

    return file_count, total_size


def _zip_generated_files(content_map, out_zip):
    import zipfile
    """
    Write in-memory content dict {filename: content_str} directly into a zip.
    Returns file_count.
    """
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in content_map.items():
            zf.writestr(name, content)
    return len(content_map)


def _detect_mode(instructions, filename):
    """
    Returns 'folder', 'files', or 'generate'.
    folder   → zip an existing folder
    files    → zip specific existing files
    generate → generate new files then zip them
    """
    low = (instructions or "").lower()

    # Explicit folder mention
    if filename and os.path.isdir(filename.strip()):
        return "folder"
    if any(w in low for w in ("folder", "directory", "whole project", "entire")):
        return "folder"

    # Generate + zip
    if any(w in low for w in ("generate", "create files", "write files",
                               "create and zip", "make and zip", "build and zip")):
        return "generate"

    # Default: zip specific files
    return "files"


# ── Entry point ───────────────────────────────────────────────────────────────

def run(filename=None, instructions=None, **kwargs):

    mode = _detect_mode(instructions, filename)

    # ── FOLDER MODE ───────────────────────────────────────────────────────
    if mode == "folder":

        folder = ""
        if filename:
            candidate = filename.strip()
            if os.path.isdir(candidate):
                folder = candidate
            elif os.path.isdir(os.path.join(BASE_DIR, candidate)):
                folder = os.path.join(BASE_DIR, candidate)

        if not folder:
            folder = input("  Folder to zip (Enter = current directory): ").strip() or BASE_DIR

        if not os.path.isdir(folder):
            print(f"  ❌ Folder not found: {folder}")
            return

        folder_name = os.path.basename(folder.rstrip("/\\"))
        out_default = os.path.join(os.path.dirname(folder) or BASE_DIR, folder_name + ".zip")
        out_zip     = input(f"  Output zip file [{out_default}]: ").strip() or out_default

        if not out_zip.endswith(".zip"):
            out_zip += ".zip"

        ok, reason = run_write_guardrails(out_zip)
        if not ok:
            print(f"  Blocked: {reason}")
            return

        if os.path.exists(out_zip):
            if not confirm(f"  '{os.path.basename(out_zip)}' already exists. Overwrite? (yes/no): "):
                return

        # Count files first for preview
        preview_files = []
        ex = {"__pycache__", ".git", "node_modules", ".agent_bin"}
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in ex]
            for f in files:
                preview_files.append(os.path.relpath(os.path.join(root, f), folder))

        print(f"\n  Folder   : {folder}")
        print(f"  Output   : {out_zip}")
        print(f"  Files    : {len(preview_files)}")
        if len(preview_files) <= 15:
            for pf in preview_files:
                print(f"             • {pf}")
        else:
            for pf in preview_files[:10]:
                print(f"             • {pf}")
            print(f"             ... and {len(preview_files)-10} more")

        if not confirm(f"\n  Zip '{folder_name}' → '{os.path.basename(out_zip)}'? (yes/no): "):
            print("  Cancelled.")
            return

        print("  Compressing...")
        count, size = _zip_folder(folder, out_zip)
        zip_size    = os.path.getsize(out_zip)
        ratio       = (1 - zip_size / size) * 100 if size else 0
        print(f"\n  ✅ Created: {out_zip}")
        print(f"     {count} files  |  {_format_size(size)} → {_format_size(zip_size)} ({ratio:.0f}% compression)")

    # ── FILES MODE ────────────────────────────────────────────────────────
    elif mode == "files":

        files = resolve_multi(filename, instructions)

        if not files:
            # Ask interactively
            print("  No files identified. Enter file paths to zip:")
            raw_paths = input("  Paths (comma-separated): ").strip()
            files = [p.strip() for p in raw_paths.split(",") if p.strip()]
            files = [p for p in files if os.path.isfile(p)]

        if not files:
            print("  No valid files found.")
            return

        out_default = os.path.join(os.path.dirname(files[0]) or BASE_DIR, "archive.zip")
        out_zip     = input(f"\n  Output zip file [{out_default}]: ").strip() or out_default
        if not out_zip.endswith(".zip"):
            out_zip += ".zip"

        ok, reason = run_write_guardrails(out_zip)
        if not ok:
            print(f"  Blocked: {reason}")
            return

        if os.path.exists(out_zip) and not confirm(f"  '{os.path.basename(out_zip)}' exists. Overwrite? (yes/no): "):
            return

        print(f"\n  Files to zip:")
        for f in files:
            print(f"    • {f}  ({_format_size(os.path.getsize(f))})")
        print(f"  Output: {out_zip}")

        if not confirm("\n  Create zip? (yes/no): "):
            print("  Cancelled.")
            return

        count, size = _zip_files(files, out_zip)
        zip_size    = os.path.getsize(out_zip)
        ratio       = (1 - zip_size / size) * 100 if size else 0
        print(f"\n  ✅ Created: {out_zip}")
        print(f"     {count} files  |  {_format_size(size)} → {_format_size(zip_size)} ({ratio:.0f}% compression)")

    # ── GENERATE + ZIP MODE ───────────────────────────────────────────────
    elif mode == "generate":

        from ..prompts import multi_file_prompt, validation_prompt
        from ..llm import call_llm
        from ..utils import clean_output
        from .create_file import parse_files

        print("  Generating files...")
        prompt     = multi_file_prompt(instructions)
        result     = clean_output(call_llm(prompt))

        # Validation loop
        validation = call_llm(validation_prompt(result))
        attempts   = 0
        while "INVALID" in validation.upper() and attempts < 3:
            print(f"  ⚠  Model output invalid (attempt {attempts+1}), retrying...")
            result     = clean_output(call_llm(prompt))
            validation = call_llm(validation_prompt(result))
            attempts  += 1

        files_map = parse_files(result)

        if not files_map:
            print("  Model did not produce any files.")
            return

        print(f"\n  Files to generate and zip:")
        for fname in files_map:
            print(f"    • {fname}  ({len(files_map[fname])} chars)")

        # Ask for zip output name
        out_default = os.path.join(BASE_DIR, "generated.zip")
        out_zip     = input(f"\n  Output zip file [{out_default}]: ").strip() or out_default
        if not out_zip.endswith(".zip"):
            out_zip += ".zip"

        ok, reason = run_write_guardrails(out_zip)
        if not ok:
            print(f"  Blocked: {reason}")
            return

        # Ask: also save files to disk?
        save_to_disk = confirm("  Also save files to disk (in addition to zip)? (yes/no): ")

        if not confirm(f"\n  Generate and zip {len(files_map)} files → '{os.path.basename(out_zip)}'? (yes/no): "):
            print("  Cancelled.")
            return

        # Write zip directly from memory
        count = _zip_generated_files(files_map, out_zip)

        # Optionally also write to disk
        if save_to_disk:
            from ..file_io import write_file
            import os as _os
            for fpath, content in files_map.items():
                folder = _os.path.dirname(fpath)
                if folder:
                    _os.makedirs(folder, exist_ok=True)
                write_file(fpath, content)
                print(f"  💾 Saved: {fpath}")

        zip_size = os.path.getsize(out_zip)
        print(f"\n  ✅ Created: {out_zip}")
        print(f"     {count} files packed  |  {_format_size(zip_size)}")
