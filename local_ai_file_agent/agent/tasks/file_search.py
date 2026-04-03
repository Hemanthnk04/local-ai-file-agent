"""
FILE_SEARCH — find files by name pattern OR grep content across folder.

Modes (auto-detected from instructions):
  name    → find files whose name matches a pattern
  content → grep for text inside files
"""

import os
import re
import fnmatch
from ..config import BASE_DIR, IGNORE_DIRS, IGNORE_EXT

# All extensions that can meaningfully be grepped for text content
SEARCHABLE_EXTS = {
    # data
    ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml",
    # documents
    ".txt", ".md", ".markdown", ".html", ".htm",
    # code
    ".py", ".pyw", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".sql", ".css", ".cpp", ".c", ".cs",
    ".go", ".rb", ".php", ".sh", ".bash", ".zsh",
    # config
    ".toml", ".ini", ".cfg", ".env",
    # misc text
    ".gitignore", ".editorconfig", ".log", ".rst",
}


def _parse_mode(instructions):
    """Return ('name', pattern) or ('content', term) or (None, None)."""
    if not instructions:
        return None, None

    low = instructions.lower()

    content_kw = ("containing", "contains", "with text", "grep", "inside",
                  "that has", "content", "search for", "find text", "look for text")
    if any(k in low for k in content_kw):
        m = re.search(r'["\']([^"\']+)["\']', instructions)
        if m:
            return "content", m.group(1)
        for kw in sorted(content_kw, key=len, reverse=True):
            idx = low.find(kw)
            if idx != -1:
                rest = instructions[idx + len(kw):].strip().strip("'\"")
                term = rest.split()[0] if rest.split() else ""
                if term:
                    return "content", term

    # Name pattern
    m = re.search(r'["\']([^"\']+)["\']', instructions)
    if m:
        return "name", m.group(1)
    m = re.search(r'\*\.\w+', instructions)
    if m:
        return "name", m.group(0)
    m = re.search(r'\b([\w.*?-]+\.[\w*]{1,6})\b', instructions)
    if m:
        return "name", m.group(1)

    return None, None


def _walk(folder):
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if any(f.endswith(e) for e in IGNORE_EXT):
                continue
            yield os.path.join(root, f)


def search_by_name(folder, pattern):
    """Find files matching a glob or substring pattern (case-insensitive)."""
    results = []
    pat_lower = pattern.lower()
    for path in _walk(folder):
        name = os.path.basename(path).lower()
        if fnmatch.fnmatch(name, pat_lower) or pat_lower in name:
            results.append(path)
    return results


def search_by_content(folder, term, extensions=None):
    """
    Grep for term inside text files.
    Returns list of (filepath, line_number, line_text).
    """
    results    = []
    term_lower = term.lower()
    search_exts = extensions or SEARCHABLE_EXTS

    for path in _walk(folder):
        ext = os.path.splitext(path)[1].lower()
        if ext not in search_exts:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if term_lower in line.lower():
                        results.append((path, lineno, line.rstrip()))
        except Exception:
            continue

    return results


def _display_name_results(results, folder):
    if not results:
        print("  No files found.")
        return
    print(f"\n  Found {len(results)} file(s):\n")
    for path in results:
        rel      = os.path.relpath(path, folder)
        size     = os.path.getsize(path)
        size_str = f"{size:,} B" if size < 1024 else f"{size//1024:,} KB"
        print(f"    {rel}  ({size_str})")


def _display_content_results(results, term, folder):
    if not results:
        print(f"  No matches for '{term}'.")
        return
    files_hit = len(set(p for p, _, _ in results))
    print(f"\n  Found {len(results)} match(es) in {files_hit} file(s) for '{term}':\n")
    current = None
    for path, lineno, line in results:
        if path != current:
            print(f"  📄 {os.path.relpath(path, folder)}")
            current = path
        hi = re.sub(re.escape(term), f"[{term}]", line, flags=re.IGNORECASE)
        print(f"      L{lineno:>4}: {hi[:120]}")


def run(filename=None, instructions=None, **kwargs):

    # Resolve search folder
    folder = ""
    if filename:
        candidate = filename.strip()
        if os.path.isdir(candidate):
            folder = candidate
        elif os.path.isdir(os.path.join(BASE_DIR, candidate)):
            folder = os.path.join(BASE_DIR, candidate)

    if not folder:
        folder = input("  Search folder (Enter = current directory): ").strip() or BASE_DIR

    if not os.path.isdir(folder):
        print(f"  Folder not found: {folder}")
        return

    mode, term = _parse_mode(instructions)

    if not mode:
        print("  Search mode:")
        print("    1. Find files by name / pattern")
        print("    2. Search file contents (grep)")
        choice = input("  Select (1/2): ").strip()
        mode = "name" if choice == "1" else "content"

    if not term:
        if mode == "name":
            term = input("  Filename or pattern (e.g. *.csv, report, main): ").strip()
        else:
            term = input("  Text to search for: ").strip()

    if not term:
        print("  No search term provided.")
        return

    print(f"\n  Searching in: {folder}")

    if mode == "name":
        print(f"  Pattern: {term}\n")
        results = search_by_name(folder, term)
        _display_name_results(results, folder)
    else:
        print(f"  Grep: '{term}'  (searching {len(SEARCHABLE_EXTS)} file types)\n")
        results = search_by_content(folder, term)
        _display_content_results(results, term, folder)
