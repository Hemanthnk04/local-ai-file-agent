"""
GENERATE_CODE — generate code in any programming language and save it.

Keeps generate_code_py untouched (Python stays as its own task).
This task handles all other languages: Java, JavaScript, TypeScript,
C, C++, C#, Go, Ruby, PHP, SQL, CSS, HTML, Bash, YAML, TOML, etc.
"""

import os
from ..prompts import code_prompt
from ..llm import call_llm
from ..utils import clean_output, confirm
from ..file_io import write_file
from ..guardrails import run_write_guardrails
from ..content_validator import validate_content

# Map common language keywords → (language_label, default_extension)
LANG_ALIASES = {
    # name           label           ext
    "python":       ("python",      ".py"),
    "py":           ("python",      ".py"),
    "javascript":   ("javascript",  ".js"),
    "js":           ("javascript",  ".js"),
    "typescript":   ("typescript",  ".ts"),
    "ts":           ("typescript",  ".ts"),
    "jsx":          ("javascript",  ".jsx"),
    "tsx":          ("typescript",  ".tsx"),
    "java":         ("java",        ".java"),
    "csharp":       ("csharp",      ".cs"),
    "c#":           ("csharp",      ".cs"),
    "cs":           ("csharp",      ".cs"),
    "cpp":          ("cpp",         ".cpp"),
    "c++":          ("cpp",         ".cpp"),
    "c":            ("c",           ".c"),
    "go":           ("go",          ".go"),
    "golang":       ("go",          ".go"),
    "ruby":         ("ruby",        ".rb"),
    "rb":           ("ruby",        ".rb"),
    "php":          ("php",         ".php"),
    "sql":          ("sql",         ".sql"),
    "css":          ("css",         ".css"),
    "html":         ("html",        ".html"),
    "bash":         ("bash",        ".sh"),
    "shell":        ("bash",        ".sh"),
    "sh":           ("bash",        ".sh"),
    "yaml":         ("yaml",        ".yaml"),
    "yml":          ("yaml",        ".yaml"),
    "toml":         ("toml",        ".toml"),
    "xml":          ("xml",         ".xml"),
    "markdown":     ("markdown",    ".md"),
    "md":           ("markdown",    ".md"),
}

# Extensions whose write is blocked by guardrails
WRITE_BLOCKED_EXTS = {".sh", ".bash", ".zsh", ".bat", ".ps1", ".cmd"}


def _detect_language(instructions, filename):
    """
    Detect the target language from:
    1. The filename extension (most reliable)
    2. Explicit language mention in instructions
    Returns (language_label, default_ext) or (None, None)
    """
    import re

    # 1. From filename extension
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext:
            # find matching label
            for label, default_ext in LANG_ALIASES.values():
                if default_ext == ext:
                    return label, ext
            # unknown ext — still use it
            return ext.lstrip("."), ext

    # 2. From instruction text — sort by length desc so "c++" matches before "c"
    low = instructions.lower() if instructions else ""
    for alias in sorted(LANG_ALIASES.keys(), key=len, reverse=True):
        label, ext = LANG_ALIASES[alias]
        # For aliases with special chars (c++, c#), use plain substring match with word boundary on left
        if any(c in alias for c in ("+", "#")):
            # match "c++" or "c#" as whole token
            pattern = r"(?<![\w])" + re.escape(alias) + r"(?![\w])"
        elif alias == "c":
            # "c" must be a standalone word, not inside another word
            pattern = r"(?<![\w])c(?![\w++#]|s\b|ss\b)"
        else:
            pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, low):
            return label, ext

    return None, None


def _default_filename(language, label, instructions):
    """Derive a sensible default filename from language + instructions."""
    import re

    # Java special case: class name from instructions
    if language == "java":
        m = re.search(r'\b([A-Z][A-Za-z0-9]+)\b', instructions or "")
        if m:
            return m.group(1) + ".java"
        return "Main.java"

    # Extract a noun from the instructions for the filename
    snake = re.sub(r'\s+', '_', (instructions or "code")[:30].strip().lower())
    snake = re.sub(r'[^\w]', '', snake).strip('_') or "code"

    ext_map = {
        "python": ".py", "javascript": ".js", "typescript": ".ts",
        "java": ".java", "csharp": ".cs", "cpp": ".cpp", "c": ".c",
        "go": ".go", "ruby": ".rb", "php": ".php", "sql": ".sql",
        "css": ".css", "html": ".html", "bash": ".sh",
        "yaml": ".yaml", "toml": ".toml", "xml": ".xml", "markdown": ".md",
    }
    ext = ext_map.get(language, label if label.startswith(".") else "." + label)
    return snake + ext


def run(filename=None, instructions=None, **kwargs):

    if not instructions:
        print("  No instructions provided.")
        return

    # Detect language
    language, default_ext = _detect_language(instructions, filename)

    if not language:
        # Default to Python when no language is specified
        print("  No language specified — defaulting to Python.")
        print("  (To use another language, say e.g. 'write a Java class for ...' or 'generate TypeScript code for ...')")
        print("  Supported: python, java, javascript, typescript, c, c++, c#, go, ruby, php, sql, css, html, bash, yaml, toml, xml, markdown")
        raw = input("  Enter language (press Enter to use Python): ").strip().lower()
        if not raw:
            language, default_ext = "python", ".py"
        elif raw in LANG_ALIASES:
            language, default_ext = LANG_ALIASES[raw]
        else:
            language, default_ext = raw, "." + raw

    # Determine save filename
    if filename and filename.strip():
        save_name = filename.strip()
        # If no extension, add the detected one
        if not os.path.splitext(save_name)[1]:
            save_name += default_ext
    else:
        save_name = _default_filename(language, default_ext, instructions)

    ext = os.path.splitext(save_name)[1].lower()

    # Check write guardrail BEFORE generating
    if ext in WRITE_BLOCKED_EXTS:
        print(f"\n  ⚠  Writing {ext} files (shell scripts) is blocked for safety.")
        print(f"     The code will be shown but not saved.")
        save_name = None

    # Generate
    print(f"  Generating {language} code...")

    prompt = code_prompt(language, instructions, filename=save_name)
    code   = clean_output(call_llm(prompt))

    # Display
    print(f"\n{'─'*52}")
    print(f"  GENERATED {language.upper()} CODE")
    print(f"{'─'*52}\n")
    print(code)
    print()

    if not save_name:
        print("  (Not saved — shell script write is blocked)")
        return

    # Java: warn if filename doesn't match class name
    if language == "java":
        import re
        m = re.search(r'\bpublic\s+class\s+(\w+)', code)
        if m:
            class_name = m.group(1)
            expected   = class_name + ".java"
            if save_name != expected and not save_name.endswith("/" + expected):
                print(f"  ⚠  Java class is '{class_name}' — filename should be '{expected}'")
                fix = input(f"  Rename to '{expected}'? (yes/no): ").strip().lower()
                if fix in ("yes", "y"):
                    save_name = expected

    ok, reason = run_write_guardrails(save_name)
    if not ok:
        print(f"\n  Blocked: {reason}")
        return

    # Ask for save folder if not specified in filename
    if not os.path.dirname(save_name):
        folder = input(f"  Save to which folder? (Enter = current directory): ").strip()
        if folder:
            os.makedirs(folder, exist_ok=True)
            save_name = os.path.join(folder, save_name)

    if not confirm(f"Save to '{save_name}'? (yes/no): "):
        print("  Cancelled.")
        return

    # Validate before saving
    val_ok, val_reason, clean_code = validate_content(code, save_name)
    if not val_ok:
        print(f"  ⚠  Content validation: {val_reason}")
        if not confirm("  Save anyway? (yes/no): "):
            print("  Cancelled.")
            return
        clean_code = code
    write_file(save_name, clean_code)
    print(f"  ✅ Saved: {save_name}  [{val_reason}]")
