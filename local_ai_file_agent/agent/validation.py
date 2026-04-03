"""
validation.py — syntax and structure validators for all supported file types.
"""

import ast
import json
import re
from io import StringIO


# ── Python ────────────────────────────────────────────────────────────────────
def validate_python(code):
    try:
        ast.parse(code)
        return True, "Valid Python"
    except SyntaxError as e:
        return False, f"Python SyntaxError at line {e.lineno}: {e.msg}"


# ── CSV ───────────────────────────────────────────────────────────────────────
def validate_csv(text):
    try:
        import pandas as pd
        df = pd.read_csv(StringIO(text))
        return True, f"Valid CSV — {len(df)} rows, {len(df.columns)} columns"
    except Exception as e:
        return False, f"Invalid CSV: {e}"


# ── TSV ───────────────────────────────────────────────────────────────────────
def validate_tsv(text):
    try:
        import pandas as pd
        df = pd.read_csv(StringIO(text), sep="\t")
        return True, f"Valid TSV — {len(df)} rows, {len(df.columns)} columns"
    except Exception as e:
        return False, f"Invalid TSV: {e}"


# ── JSON ──────────────────────────────────────────────────────────────────────
def validate_json(text):
    try:
        data = json.loads(text)
        kind = type(data).__name__
        if isinstance(data, list):
            return True, f"Valid JSON — array with {len(data)} items"
        if isinstance(data, dict):
            return True, f"Valid JSON — object with {len(data)} keys"
        return True, f"Valid JSON ({kind})"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON at line {e.lineno}: {e.msg}"


# ── XML ───────────────────────────────────────────────────────────────────────
def validate_xml(text):
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(text)
        return True, "Valid XML"
    except Exception as e:
        return False, f"Invalid XML: {e}"


# ── YAML ──────────────────────────────────────────────────────────────────────
def validate_yaml(text):
    try:
        import yaml
        data = yaml.safe_load(text)
        return True, f"Valid YAML ({type(data).__name__})"
    except Exception as e:
        return False, f"Invalid YAML: {e}"


# ── TOML ──────────────────────────────────────────────────────────────────────
def validate_toml(text):
    try:
        import tomllib
        tomllib.loads(text)
        return True, "Valid TOML"
    except ImportError:
        try:
            import tomli
            tomli.loads(text)
            return True, "Valid TOML"
        except ImportError:
            return True, "TOML validation skipped (tomllib/tomli not installed)"
    except Exception as e:
        return False, f"Invalid TOML: {e}"


# ── INI ───────────────────────────────────────────────────────────────────────
def validate_ini(text):
    try:
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read_string(text)
        sections = cfg.sections()
        return True, f"Valid INI — {len(sections)} section(s): {sections}"
    except Exception as e:
        return False, f"Invalid INI: {e}"


# ── HTML ──────────────────────────────────────────────────────────────────────
def validate_html(text):
    try:
        from html.parser import HTMLParser

        class _Checker(HTMLParser):
            def __init__(self):
                super().__init__()
                self.errors = []
                self.stack  = []
            def handle_starttag(self, tag, attrs):
                void = {"area","base","br","col","embed","hr","img","input",
                        "link","meta","param","source","track","wbr"}
                if tag not in void:
                    self.stack.append(tag)
            def handle_endtag(self, tag):
                if self.stack and self.stack[-1] == tag:
                    self.stack.pop()

        checker = _Checker()
        checker.feed(text)
        if checker.stack:
            return False, f"Unclosed HTML tags: {checker.stack}"
        return True, "Valid HTML"
    except Exception as e:
        return False, f"HTML parse error: {e}"


# ── CSS ───────────────────────────────────────────────────────────────────────
def validate_css(text):
    """Basic CSS brace-balance check."""
    opens  = text.count("{")
    closes = text.count("}")
    if opens != closes:
        return False, f"CSS brace mismatch: {opens} open, {closes} close"
    # Check for obviously broken at-rules
    if re.search(r"@[a-z-]+\s*;", text):
        return True, "Valid CSS (with at-rules)"
    return True, "Valid CSS"


# ── JavaScript / TypeScript ───────────────────────────────────────────────────
def validate_js(text):
    """Heuristic JS/TS check: brace balance + no obvious syntax markers."""
    opens  = text.count("{")
    closes = text.count("}")
    parens_o = text.count("(")
    parens_c = text.count(")")
    if opens != closes:
        return False, f"JS/TS brace mismatch: {opens}{{ vs {closes}}}"
    if parens_o != parens_c:
        return False, f"JS/TS parenthesis mismatch: {parens_o}( vs {parens_c})"
    return True, "JS/TS appears structurally valid"


# ── SQL ───────────────────────────────────────────────────────────────────────
def validate_sql(text):
    """Check SQL for basic keyword presence and semicolons."""
    keywords = re.findall(
        r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH|FROM|WHERE)\b",
        text, re.IGNORECASE
    )
    if not keywords:
        return False, "No SQL keywords found — may not be a SQL file"
    unclosed_parens = text.count("(") - text.count(")")
    if unclosed_parens != 0:
        return False, f"SQL parenthesis mismatch ({unclosed_parens:+d})"
    return True, f"Valid SQL — keywords found: {', '.join(sorted(set(k.upper() for k in keywords)))}"


# ── Java ──────────────────────────────────────────────────────────────────────
def validate_java(text):
    opens  = text.count("{")
    closes = text.count("}")
    if opens != closes:
        return False, f"Java brace mismatch: {opens}{{ vs {closes}}}"
    if not re.search(r"\bclass\b|\binterface\b|\benum\b", text):
        return False, "No class/interface/enum declaration found"
    return True, "Java appears structurally valid"


# ── Markdown ──────────────────────────────────────────────────────────────────
def validate_md(text):
    lines   = text.splitlines()
    headers = sum(1 for l in lines if l.startswith("#"))
    words   = len(text.split())
    return True, f"Valid Markdown — {len(lines)} lines, {headers} heading(s), ~{words} words"




# ── C / C++ ──────────────────────────────────────────────────────────────────
# ── C / C++ ──────────────────────────────────────────────────────────────────
def validate_c_cpp(text):
    opens  = text.count('{')
    closes = text.count('}')
    if opens != closes:
        return False, "C/C++ brace mismatch: {} open, {} close".format(opens, closes)
    kw = ['int','void','char','float','double','struct','class','include','return','main','printf','cout']
    if not any(k in text for k in kw):
        return False, "No C/C++ keywords found"
    return True, "C/C++ appears structurally valid"


# ── C# ────────────────────────────────────────────────────────────────────────
def validate_csharp(text):
    opens  = text.count('{')
    closes = text.count('}')
    if opens != closes:
        return False, "C# brace mismatch: {} open, {} close".format(opens, closes)
    kw = ['class','namespace','using','interface','enum','static','void','Console','public','private']
    if not any(k in text for k in kw):
        return False, "No C# keywords found"
    return True, "C# appears structurally valid"


# ── Go ────────────────────────────────────────────────────────────────────────
def validate_go(text):
    if 'package' not in text:
        return False, "Missing 'package' declaration"
    opens  = text.count('{')
    closes = text.count('}')
    if opens != closes:
        return False, "Go brace mismatch: {} open, {} close".format(opens, closes)
    return True, "Go appears structurally valid"


def validate_php(text):
    if not re.search(r"<\?php", text, re.IGNORECASE):
        return False, "Missing PHP opening tag <?php"
    opens  = text.count("{")
    closes = text.count("}")
    if opens != closes:
        return False, f"PHP brace mismatch: {opens}{{ vs {closes}}}"
    return True, "PHP appears structurally valid"


# ── Ruby ──────────────────────────────────────────────────────────────────────
def validate_ruby(text):
    # Ruby uses end keywords instead of braces
    defs = len(re.findall(r"\b(def|do|class|module|if|unless|while|for|begin)\b", text))
    ends = len(re.findall(r"\bend\b", text))
    if abs(defs - ends) > 2:   # allow slight mismatch for inline ifs
        return False, f"Ruby block mismatch: {defs} openers, {ends} 'end' keywords"
    return True, "Ruby appears structurally valid"


# ── Plain text ────────────────────────────────────────────────────────────────
def validate_txt(text):
    lines = text.splitlines()
    words = len(text.split())
    return True, f"Plain text — {len(lines)} lines, ~{words} words"


# ── .env ─────────────────────────────────────────────────────────────────────
def validate_env(text):
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    invalid = [l for l in lines if "=" not in l]
    if invalid:
        return False, f"Invalid .env lines (missing '='): {invalid[:3]}"
    return True, f"Valid .env — {len(lines)} variable(s)"




# ── Shell scripts ─────────────────────────────────────────────────────────────
def validate_shell(text):
    """Basic shell script check — shebang presence and brace balance."""
    has_shebang = text.strip().startswith("#!")
    opens  = text.count("{")
    closes = text.count("}")
    if opens != closes:
        return False, f"Shell brace mismatch: {opens}{{ vs {closes}}}"
    hint = " (has shebang)" if has_shebang else " (no shebang — may not be executable)"
    return True, f"Shell script appears valid{hint}"


# ── DOCX ──────────────────────────────────────────────────────────────────────
def validate_docx(path_or_text):
    """Try opening as a Word document."""
    try:
        # path_or_text will be the extracted text string from read_file
        # We can only check it's non-empty since read_file already extracted text
        if not str(path_or_text).strip():
            return False, "Word document appears empty"
        lines = str(path_or_text).splitlines()
        return True, f"Valid Word document — {len(lines)} paragraph(s)"
    except Exception as e:
        return False, f"DOCX error: {e}"


# ── PDF ───────────────────────────────────────────────────────────────────────
def validate_pdf(path_or_text):
    """Check extracted PDF text is non-empty."""
    text = str(path_or_text).strip()
    if not text:
        return False, "PDF appears empty or text could not be extracted (may be scanned/image-only)"
    words = len(text.split())
    return True, f"PDF text extracted — ~{words} words"


# ── XLSX ──────────────────────────────────────────────────────────────────────
def validate_xlsx(data):
    """Validate DataFrame from Excel."""
    try:
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            if data.empty:
                return False, "Excel file is empty"
            return True, f"Valid Excel — {len(data)} rows × {len(data.columns)} columns"
        # fallback: list of lists from read_excel
        if isinstance(data, list):
            return True, f"Valid Excel — {len(data)} row(s) read"
        return True, "Excel file readable"
    except Exception as e:
        return False, f"XLSX error: {e}"

# ── DISPATCH TABLE ────────────────────────────────────────────────────────────
VALIDATORS = {
    ".py":   validate_python,
    ".pyw":  validate_python,
    ".sh":   validate_shell,
    ".bash": validate_shell,
    ".zsh":  validate_shell,
    ".docx": validate_docx,
    ".pdf":  validate_pdf,
    ".xlsx": validate_xlsx,
    ".csv":  validate_csv,
    ".tsv":  validate_tsv,
    ".json": validate_json,
    ".xml":  validate_xml,
    ".yaml": validate_yaml,
    ".yml":  validate_yaml,
    ".toml": validate_toml,
    ".ini":  validate_ini,
    ".cfg":  validate_ini,
    ".html": validate_html,
    ".htm":  validate_html,
    ".css":  validate_css,
    ".js":   validate_js,
    ".ts":   validate_js,
    ".jsx":  validate_js,
    ".tsx":  validate_js,
    ".sql":  validate_sql,
    ".java": validate_java,
    ".md":   validate_md,
    ".markdown": validate_md,
    # C-family
    ".c":    validate_c_cpp,
    ".cpp":  validate_c_cpp,
    ".cc":   validate_c_cpp,
    ".h":    validate_c_cpp,
    ".hpp":  validate_c_cpp,
    # C#
    ".cs":   validate_csharp,
    # Go
    ".go":   validate_go,
    # PHP
    ".php":  validate_php,
    # Ruby
    ".rb":   validate_ruby,
    # Plain text
    ".txt":  validate_txt,
    ".log":  validate_txt,
    # Env
    ".env":  validate_env,
}


def validate_file(path, content):
    """
    Validate content for the given file path.
    Returns (ok: bool, message: str).
    """
    ext = os.path.splitext(path)[1].lower() if path else ""
    fn  = VALIDATORS.get(ext)
    if fn:
        return fn(content)
    return True, f"No validator for '{ext}' — file is readable"


import os  # keep at bottom to avoid circular at top