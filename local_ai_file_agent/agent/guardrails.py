"""
guardrails.py — all safety checks for the file agent.

Functions return (ok: bool, reason: str).
ok=False means BLOCK or WARN — the caller decides which.
"""

import os
import re
from .config import BLOCKED_EXTENSIONS

# Extensions that are code (not data) — used to pick the right loss check
CODE_EXTS = {
    ".py", ".pyw", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs",
    ".cpp", ".c", ".go", ".rb", ".php", ".sql", ".css", ".html",
    ".htm", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".xml", ".md", ".markdown", ".json",
}

DATA_EXTS = {".csv", ".tsv", ".xlsx"}


# ── Pre-write guardrails ──────────────────────────────────────────────────────

def check_extension(filename):
    """Block writing to dangerous executable/script file types."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        return False, f"Writing '{ext}' files is blocked for safety."
    return True, ""


def check_path_traversal(filename):
    """Block paths that try to escape the working directory."""
    norm = os.path.normpath(filename)
    if norm.startswith(".."):
        return False, f"Path traversal blocked: '{filename}'"
    return True, ""


def run_write_guardrails(filename):
    """Run all pre-write guardrails. Returns (ok, reason)."""
    for check in [check_extension, check_path_traversal]:
        ok, reason = check(filename)
        if not ok:
            return False, reason
    return True, ""


def check_overwrite(filepath):
    """Returns (exists, filepath) — caller decides whether to warn."""
    return os.path.exists(filepath), filepath


# ── Post-generation content guardrails ───────────────────────────────────────

def check_row_loss(original_text, new_text, threshold=0.2):
    """
    DATA FILE guardrail — fires when rewritten content loses >threshold of lines.
    Used for .csv / .tsv / .xlsx (tabular data where every row matters).
    Returns (ok, reason).  ok=False → warn user before writing.
    """
    orig_lines = [l for l in original_text.splitlines() if l.strip()]
    new_lines  = [l for l in new_text.splitlines()      if l.strip()]

    if not orig_lines:
        return True, ""

    loss_ratio = 1.0 - (len(new_lines) / len(orig_lines))

    if loss_ratio > threshold:
        lost = len(orig_lines) - len(new_lines)
        return False, (
            f"⚠  Row-loss guardrail: original had {len(orig_lines)} lines, "
            f"rewrite has {len(new_lines)} ({lost} removed, {loss_ratio:.0%} reduction).\n"
            f"   The model may have deleted data rows it shouldn't have."
        )

    return True, ""


def _extract_code_symbols(text, ext):
    """
    Extract function/class/method names from source code.
    Returns a set of symbol names found.
    """
    symbols = set()
    ext = ext.lower()

    if ext in (".py", ".pyw"):
        symbols |= set(re.findall(r"^\s*(?:def|class)\s+(\w+)", text, re.M))

    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        symbols |= set(re.findall(r"(?:function\s+(\w+)|class\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()", text))
        symbols = {s for tup in symbols for s in tup if s}

    elif ext == ".java":
        symbols |= set(re.findall(r"(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(", text, re.M))
        symbols |= set(re.findall(r"\bclass\s+(\w+)", text))

    elif ext in (".cs",):
        symbols |= set(re.findall(r"(?:public|private|protected|internal)?\s*(?:static\s+)?(?:override\s+)?[\w<>\[\]]+\s+(\w+)\s*\(", text, re.M))
        symbols |= set(re.findall(r"\bclass\s+(\w+)", text))

    elif ext in (".cpp", ".c"):
        symbols |= set(re.findall(r"^\w[\w\s*<>:]+\s+(\w+)\s*\([^;]*\)\s*\{", text, re.M))

    elif ext == ".go":
        symbols |= set(re.findall(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", text, re.M))

    elif ext in (".rb",):
        symbols |= set(re.findall(r"^\s*def\s+(\w+)", text, re.M))

    elif ext == ".php":
        symbols |= set(re.findall(r"function\s+(\w+)\s*\(", text))

    elif ext == ".sql":
        symbols |= set(re.findall(r"(?:CREATE|DROP|ALTER)\s+(?:TABLE|VIEW|PROCEDURE|FUNCTION)\s+(\w+)", text, re.I))

    # Generic fallback — count meaningful lines for all other types
    return symbols


def check_code_reduction(original_text, new_text, filename):
    """
    CODE FILE guardrail — fires when rewritten code:
    (a) loses functions/classes that were in the original, OR
    (b) shrinks by more than 40% in line count without an explicit reduction instruction.

    Returns (ok, reason). ok=False → warn user.
    """
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext not in CODE_EXTS:
        return True, ""

    orig_lines = [l for l in original_text.splitlines() if l.strip()]
    new_lines  = [l for l in new_text.splitlines()      if l.strip()]

    if not orig_lines:
        return True, ""

    # (a) Symbol-level check — detect dropped functions/classes
    orig_symbols = _extract_code_symbols(original_text, ext)
    new_symbols  = _extract_code_symbols(new_text, ext)

    if orig_symbols and new_symbols:
        dropped = orig_symbols - new_symbols
        if dropped:
            return False, (
                f"⚠  Code-reduction guardrail: {len(dropped)} symbol(s) present in original "
                f"are MISSING from the rewrite:\n"
                f"   {', '.join(sorted(dropped))}\n"
                f"   The model may have silently deleted functions or classes."
            )

    # (b) Line-count check — 40% threshold for code (more lenient than data)
    loss_ratio = 1.0 - (len(new_lines) / len(orig_lines))
    if loss_ratio > 0.40:
        lost = len(orig_lines) - len(new_lines)
        return False, (
            f"⚠  Code-reduction guardrail: original had {len(orig_lines)} lines, "
            f"rewrite has {len(new_lines)} ({lost} lines removed, {loss_ratio:.0%} reduction).\n"
            f"   The model may have truncated code it was told to preserve."
        )

    return True, ""


def check_content_reduction(original_text, new_text, filename):
    """
    Master dispatcher — picks the right guardrail based on file type.
    Returns (ok, reason).
    """
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext in DATA_EXTS:
        return check_row_loss(original_text, new_text)

    if ext in CODE_EXTS:
        return check_code_reduction(original_text, new_text, filename)

    # Plain text / docs — light check at 50% threshold
    orig_lines = [l for l in original_text.splitlines() if l.strip()]
    new_lines  = [l for l in new_text.splitlines()      if l.strip()]
    if orig_lines:
        loss_ratio = 1.0 - (len(new_lines) / len(orig_lines))
        if loss_ratio > 0.50:
            return False, (
                f"⚠  Content-reduction guardrail: original had {len(orig_lines)} lines, "
                f"rewrite has {len(new_lines)} ({loss_ratio:.0%} reduction)."
            )

    return True, ""
