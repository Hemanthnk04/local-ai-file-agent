"""
Smart filename resolution.

Priority order:
  1. Model-provided filename (from classifier JSON)  — use if file exists on disk
  2. Scan cwd for files matching the name            — handle relative names
  3. Scan cwd for files with a matching extension    — fuzzy fallback
  4. Ask the user                                    — last resort only
"""

import os
import re
from .config import BASE_DIR


SUPPORTED_EXT = {
    # data
    ".csv", ".tsv", ".json", ".xlsx", ".xml", ".yaml", ".yml",
    # documents
    ".txt", ".md", ".pdf", ".docx", ".html", ".htm",
    # code
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".sql",
    ".css", ".cpp", ".c", ".cs", ".go", ".rb", ".php",
    # config
    ".toml", ".ini", ".cfg", ".env",
    # shell / other
    ".sh", ".bash", ".zsh", ".pyw", ".markdown",
    # archives
    ".zip",
}


def _exists(path):
    return path and os.path.isfile(path)


def _find_in_cwd(name):
    """Search BASE_DIR recursively for a file whose basename matches `name`."""
    name_lower = name.lower()
    _skip = {"__pycache__", ".git", "node_modules", ".agent_bin", ".agent_logs"}
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in _skip]
        for f in files:
            if f.lower() == name_lower:
                return os.path.join(root, f)
    return None


def _scan_by_extension(ext):
    """Return all files in BASE_DIR with the given extension."""
    matches = []
    _skip = {"__pycache__", ".git", "node_modules", ".agent_bin", ".agent_logs"}
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in _skip]
        for f in files:
            if f.lower().endswith(ext):
                matches.append(os.path.join(root, f))
    return matches


def resolve_single(model_filename, instructions=None, prompt_label="file"):
    """
    Resolve one filename to a real path.
    Returns the resolved path, or None if user skipped.
    """

    # ── 1. Model gave a filename and it exists as-is ──────────────────────
    if model_filename:
        candidate = model_filename.strip()

        if _exists(candidate):
            return candidate

        # try relative to BASE_DIR
        rel = os.path.join(BASE_DIR, candidate)
        if _exists(rel):
            return rel

        # try just the basename inside cwd
        found = _find_in_cwd(os.path.basename(candidate))
        if found:
            print(f"📂 Located '{os.path.basename(candidate)}' at: {found}")
            return found

    # ── 2. Try to parse a filename out of the instructions ────────────────
    if instructions:
        ext_pattern = r"[\w.\-/ \\]+\.(?:py|pyw|csv|tsv|json|xlsx|xml|yaml|yml|txt|md|pdf|docx|html|htm|js|ts|jsx|tsx|java|sql|css|cpp|c|cs|go|rb|php|toml|ini|cfg|env|sh|bash|zsh|pyw|markdown|zip)"
        matches = re.findall(ext_pattern, instructions, re.IGNORECASE)
        for m in matches:
            m = m.strip()
            if _exists(m):
                return m
            rel = os.path.join(BASE_DIR, os.path.basename(m))
            if _exists(rel):
                return rel
            found = _find_in_cwd(os.path.basename(m))
            if found:
                print(f"📂 Located '{os.path.basename(m)}' at: {found}")
                return found

    # ── 3. Extension-based fuzzy match ────────────────────────────────────
    if model_filename:
        ext = os.path.splitext(model_filename)[1].lower()
        if ext in SUPPORTED_EXT:
            matches = _scan_by_extension(ext)
            if len(matches) == 1:
                print(f"📂 Only one {ext} file found, using: {matches[0]}")
                return matches[0]
            if matches:
                print(f"\nMultiple {ext} files found:")
                for i, p in enumerate(matches):
                    print(f"  [{i}] {p}")
                raw = input("Select file number (or press Enter to type path): ").strip()
                if raw.isdigit() and int(raw) < len(matches):
                    return matches[int(raw)]

    # ── 4. Ask the user ───────────────────────────────────────────────────
    hint = f" for '{model_filename}'" if model_filename else ""
    path = input(f"\nEnter path{hint} (or press Enter to skip): ").strip()
    if path and _exists(path):
        return path
    if path:
        print(f"File not found: {path}")
    return None


def resolve_multi(model_filename, instructions=None):
    """
    Resolve a comma-separated list of filenames to real paths.
    Returns list of resolved paths.
    """
    if not model_filename:
        # try from instructions
        single = resolve_single(None, instructions)
        return [single] if single else []

    names = [n.strip() for n in model_filename.split(",") if n.strip()]
    results = []
    for name in names:
        path = resolve_single(name, instructions)
        if path:
            results.append(path)
    return results
