"""
file_io.py — unified file reader/writer.

pandas, openpyxl, docx, pypdf are all imported lazily inside functions
so they only load when a relevant file type is actually used.
"""

import os
from .config import BASE_DIR
from .guardrails import run_write_guardrails

from .document_tools import (
    create_word, read_word,
    create_pdf,  read_pdf,
    create_excel, read_excel, create_excel_multi,
)

# All extensions readable as plain UTF-8 text
TEXT_EXTS = {
    ".txt", ".md", ".markdown",
    ".html", ".htm", ".xml",
    ".css", ".js", ".ts", ".jsx", ".tsx",
    ".py", ".pyw", ".java", ".sql", ".cpp", ".c", ".cs", ".go", ".rb", ".php",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    ".json", ".tsv",
    ".sh", ".bash", ".zsh",
    ".gitignore", ".editorconfig",
}


def read_file(filename):
    if not filename:
        return None, "Filename not provided"

    path = filename if os.path.isabs(filename) else os.path.join(BASE_DIR, filename)

    if not os.path.exists(path):
        return None, "File not found"

    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".docx":
            return read_word(path), None

        if ext == ".pdf":
            return read_pdf(path), None

        if ext == ".xlsx":
            try:
                import pandas as pd
                return pd.read_excel(path), None
            except Exception:
                return read_excel(path), None

        if ext == ".csv":
            import pandas as pd
            return pd.read_csv(path), None

        if ext == ".tsv":
            import pandas as pd
            return pd.read_csv(path, sep="\t"), None

        if ext == ".zip":
            import zipfile
            if not zipfile.is_zipfile(path):
                return None, "Not a valid ZIP file"
            with zipfile.ZipFile(path, "r") as zf:
                lines = []
                for info in zf.infolist():
                    size    = info.file_size
                    size_s  = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
                    lines.append(f"  {info.filename}  ({size_s})")
            return "\n".join(lines), None

        # All text-based extensions
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), None

    except Exception as e:
        return None, str(e)


def write_file(filename, content):
    path = filename if os.path.isabs(filename) else os.path.join(BASE_DIR, filename)

    ok, reason = run_write_guardrails(filename)
    if not ok:
        print(f"Blocked: {reason}")
        return None

    ext = os.path.splitext(path)[1].lower()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    # ── Binary / rich formats ─────────────────────────────────────────────
    if ext == ".docx":
        create_word(path, str(content))
        return path

    if ext == ".pdf":
        create_pdf(path, str(content))
        return path

    if ext == ".xlsx":
        if isinstance(content, dict):
            create_excel_multi(path, content)
            return path
        try:
            import pandas as pd
            if isinstance(content, pd.DataFrame):
                content.to_excel(path, index=False)
                return path
        except ImportError:
            pass
        if isinstance(content, list):
            create_excel(path, content)
            return path
        # CSV text → excel
        try:
            import pandas as pd
            from io import StringIO
            df = pd.read_csv(StringIO(str(content)))
            df.to_excel(path, index=False)
            return path
        except Exception:
            create_excel(path, [[str(content)]])
            return path

    # ── CSV / TSV ─────────────────────────────────────────────────────────
    if ext in (".csv", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        try:
            import pandas as pd
            if isinstance(content, pd.DataFrame):
                content.to_csv(path, index=False, sep=sep)
                return path
            from io import StringIO
            df = pd.read_csv(StringIO(str(content)), sep=sep)
            df.to_csv(path, index=False, sep=sep)
            return path
        except Exception:
            pass  # fall through to text write

    # ── Plain text (code, config, markup, etc.) ───────────────────────────
    if isinstance(content, str):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    else:
        try:
            import pandas as pd
            if isinstance(content, pd.DataFrame):
                content.to_csv(path, index=False)
                return path
        except ImportError:
            pass
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(str(content))

    return path


def csv_text_to_df(text):
    try:
        import pandas as pd
        from io import StringIO
        return pd.read_csv(StringIO(text))
    except Exception:
        return None
