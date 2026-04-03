"""
SAVE_CONTENT — extract content from the user's prompt and save to file(s).

Handles all three ways a user might send content:

  1. FILE: block format (one or many):
       FILE: main.py
       def foo(): pass

  2. Inline with filename keyword:
       save this as main.py
       <content follows after newline>

  3. Previously generated content (last agent output):
       "save that as main.py"  (no inline content — uses _last_output buffer)

  4. Rewrite existing file with inline content:
       "write this to data.csv"
       id,name
       1,Alice
"""

import os
import re

from ..file_io import write_file
from ..guardrails import run_write_guardrails
from ..content_validator import validate_content, sanitize
from ..utils import confirm
from ..config import BASE_DIR


# ── File block parser (FILE: name\ncontent) ────────────────────────────────

def _parse_file_blocks(text):
    """
    Parse FILE: ... blocks from raw user input.
    Returns {filename: content} dict, or empty dict if no blocks found.
    """
    files   = {}
    current = None
    lines   = text.splitlines()

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()

        # Detect FILE: header (case-insensitive)
        if re.match(r"^FILE\s*:\s*.+", stripped, re.I):
            current = re.split(r"FILE\s*:\s*", stripped, maxsplit=1, flags=re.I)[1].strip()
            files[current] = []
            continue

        if current is None:
            continue

        # Skip common LLM filler words that appear right after FILE:
        if stripped.lower() in {"content", "contents", "file content",
                                  "here is the file", "here is the content"}:
            continue

        files[current].append(line)

    # Join and strip trailing blank lines
    return {k: "\n".join(v).strip() for k, v in files.items() if "\n".join(v).strip()}


# ── Inline content extractor ───────────────────────────────────────────────

def _extract_inline(user_input):
    """
    Extract (filename, content) from prompts like:
      "save this as main.py\ndef foo(): pass"
      "write the following to data.csv\nid,name\n1,Alice"
      "store this in config.json\n{\"key\": \"value\"}"

    Returns (filename, content) or (None, None).
    """
    lines = user_input.strip().splitlines()
    if len(lines) < 2:
        return None, None

    first = lines[0].strip()

    # Look for filename in the first line
    m = re.search(
        r"(?:save|write|store|put|export|dump)\s+(?:this|it|content|data|code|the following)?\s*"
        r"(?:as|to|in|into|at|called?|named?)\s+([\w.\-/\\]+\.[\w]+)",
        first, re.I
    )
    if not m:
        # Try simpler: "filename.ext:\n content"
        m2 = re.match(r"([\w.\-/\\]+\.\w+)\s*:\s*$", first)
        if m2:
            return m2.group(1).strip(), "\n".join(lines[1:]).strip()
        return None, None

    filename = m.group(1).strip()
    # Content is everything after the first line
    content  = "\n".join(lines[1:]).strip()

    # Strip markdown fences if present
    content = sanitize(content, os.path.splitext(filename)[1].lower())

    return filename, content if content else None


# ── Resolve save folder ────────────────────────────────────────────────────

def _resolve_path(filename, instructions):
    """
    Return a full path for the given filename.
    Asks for folder if none specified.
    """
    # If already absolute or has directory component, use as-is
    if os.path.isabs(filename) or os.path.dirname(filename):
        return filename

    # Try to detect folder from instructions (e.g. "save to src/main.py")
    m = re.search(r"(?:to|in|into|at)\s+([\w./\\-]+/)", instructions or "", re.I)
    if m:
        folder = m.group(1).rstrip("/\\")
        if os.path.isdir(folder) or os.path.isdir(os.path.join(BASE_DIR, folder)):
            return os.path.join(folder, filename)

    folder = input(f"  Save '{filename}' to which folder? (Enter = current dir): ").strip()
    if folder:
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)

    return filename


# ── Write a single file with validation + confirm ──────────────────────────

def _write_one(filename, content, instructions, skip_confirm=False):
    """
    Validate, preview, confirm, and write a single file.
    Returns True on success.
    """
    target = _resolve_path(filename, instructions)

    ok, reason = run_write_guardrails(target)
    if not ok:
        print(f"  Blocked '{target}': {reason}")
        return False

    ext = os.path.splitext(target)[1].lower()

    # Validate content
    val_ok, val_reason, clean = validate_content(content, target)
    if not val_ok:
        print(f"  ⚠  Content validation for '{filename}': {val_reason}")
        if not confirm("  Save anyway? (yes/no): "):
            print(f"  Skipped: {filename}")
            return False
        clean = content

    # Preview
    preview_lines = clean.splitlines()
    print(f"\n  ── {filename} ({'─' * max(0, 44 - len(filename))} preview) ──")
    for line in preview_lines[:12]:
        print(f"    {line}")
    if len(preview_lines) > 12:
        print(f"    ... [{len(preview_lines) - 12} more lines]")
    print(f"  [{val_reason}]")

    if not skip_confirm:
        if not confirm(f"\n  Write to '{target}'? (yes/no): "):
            print(f"  Skipped: {filename}")
            return False

    # Handle existing file
    if os.path.exists(target):
        choice = input(f"  '{target}' already exists. 1=overwrite  2=rename  3=skip: ").strip()
        if choice == "2":
            new_name = input("  New filename: ").strip()
            target   = os.path.join(os.path.dirname(target), new_name)
        elif choice == "3":
            print(f"  Skipped: {filename}")
            return False

    result = write_file(target, clean)
    if result:
        size     = os.path.getsize(result)
        size_str = f"{size:,} B" if size < 1024 else f"{size // 1024:,} KB"
        print(f"  ✅ Saved: {result}  ({size_str})")
        return True
    else:
        print(f"  ❌ Write failed: {target}")
        return False


# ── Entry point ────────────────────────────────────────────────────────────

def run(filename=None, instructions=None, pending_content=None,
        raw_user_input=None, **kwargs):
    """
    Save content to file(s). Sources tried in order:

    1. FILE: blocks inside the user's raw prompt
    2. Inline content (content after the first line of the prompt)
    3. Previously buffered agent output (pending_content)
    4. Ask user to paste content interactively
    """

    full_text = raw_user_input or ""

    # ── 1. FILE: block format ──────────────────────────────────────────────
    file_blocks = _parse_file_blocks(full_text)
    if file_blocks:
        print(f"\n  Found {len(file_blocks)} file block(s) in your prompt:")
        for name in file_blocks:
            lines = file_blocks[name].splitlines()
            print(f"    • {name}  ({len(lines)} lines)")

        if not confirm("\n  Save all? (yes/no): "):
            print("  Cancelled.")
            return

        saved = 0
        for fname, content in file_blocks.items():
            if _write_one(fname, content, instructions, skip_confirm=True):
                saved += 1

        print(f"\n  Done: {saved}/{len(file_blocks)} file(s) saved.")
        return

    # ── 2. Inline content in the prompt ───────────────────────────────────
    if full_text and "\n" in full_text:
        inline_name, inline_content = _extract_inline(full_text)
        if inline_name and inline_content:
            print(f"\n  Detected inline content for: {inline_name}")
            _write_one(inline_name, inline_content, instructions)
            return

    # ── 3. Previously buffered agent output ───────────────────────────────
    if pending_content:
        target = filename.strip() if filename else ""

        if not target:
            # Extract filename from instructions
            m = re.search(
                r"(?:as|to|into|called?|named?)\s+([\w.\-/\\]+\.[\w]+)",
                (instructions or ""), re.I
            )
            target = m.group(1).strip() if m else ""

        if not target:
            target = input("  Save as filename: ").strip()

        if not target:
            print("  No filename provided.")
            return

        _write_one(target, pending_content, instructions)
        return

    # ── 4. Interactive fallback — ask user to paste ────────────────────────
    print("  No content found in your prompt.")
    print("  You can either:")
    print("    a) Paste content in the format:  FILE: filename.ext")
    print("                                     <content here>")
    print("    b) Type:  save this as filename.ext")
    print("              <content on next lines>")
    print("    c) First generate content, then say 'save that as filename.ext'")
