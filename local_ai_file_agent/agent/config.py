"""
config.py — loads agent.config.yaml and exposes all settings as module-level constants.
Falls back to safe defaults if the config file is missing.
"""

import os

# ── Locate the project root (where main.py lives) ────────────────────────────
# This works regardless of which directory the user launches from.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Load YAML config ──────────────────────────────────────────────────────────
def _load_config():
    config_path = os.path.join(_HERE, "agent.config.yaml")
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"  ⚠  Could not read agent.config.yaml: {e} — using defaults")
        return {}

_cfg = _load_config()

# ── Paths ─────────────────────────────────────────────────────────────────────
_base = _cfg.get("paths", {}).get("base_dir", "").strip()
BASE_DIR = _base if _base else _HERE   # always anchored to project root

BIN_DIR  = os.path.join(BASE_DIR, _cfg.get("paths", {}).get("bin_dir",  ".agent_bin"))
LOG_DIR  = os.path.join(BASE_DIR, _cfg.get("paths", {}).get("log_dir",  ".agent_logs"))

# ── LLM settings ─────────────────────────────────────────────────────────────
_llm = _cfg.get("llm", {})
LLM_PROVIDER        = _llm.get("provider",              "ollama")
LLM_MODEL           = _llm.get("model",                 "qwen2.5:3b")
LLM_URL             = _llm.get("url",                   "http://localhost:11434/api/generate")
LLM_TIMEOUT         = int(_llm.get("timeout_seconds",   120))
LLM_RETRY_ATTEMPTS  = int(_llm.get("retry_attempts",    3))
LLM_RETRY_DELAY     = float(_llm.get("retry_delay_seconds", 2))

# ── Limits ────────────────────────────────────────────────────────────────────
_lim = _cfg.get("limits", {})
MAX_FILE_CHARS   = int(_lim.get("max_file_chars",      40000))
CHUNK_OVERLAP    = int(_lim.get("max_chunk_overlap",   200))
BIN_MAX_MB       = int(_lim.get("bin_max_mb",          500))
BIN_MAX_ITEMS    = int(_lim.get("bin_max_items",       1000))

# ── Agent behaviour ───────────────────────────────────────────────────────────
_agent = _cfg.get("agent", {})
INTERACTIVE  = bool(_agent.get("interactive",  True))
SHOW_DIFF    = bool(_agent.get("show_diff",    True))
AUTO_BACKUP  = bool(_agent.get("auto_backup",  True))

# ── Static constants ──────────────────────────────────────────────────────────
BLOCKED_EXTENSIONS = [
    ".exe", ".dll", ".msi",
    ".sh", ".bash", ".zsh", ".bat", ".ps1", ".cmd",
]

IGNORE_DIRS = ["__pycache__", ".git", "node_modules"]
IGNORE_EXT  = [".pyc", ".pyo", ".dll", ".so", ".dylib"]

TASK_REGISTRY = {
    "CREATE_FILE":     "Create files/folders",
    "READ_FILE":       "Read or explain file",
    "REWRITE_FILE":    "Rewrite file",
    "DIFF_PREVIEW":    "Preview rewrite diff",
    "VALIDATE_FILE":   "Validate file",
    "GENERATE_CODE":   "Generate code in any language",
    "FOLDER_ANALYSIS": "Analyze folder",
    "BATCH_OPS":       "Batch rename/delete/move files",
    "FILE_CONVERT":    "Convert file format",
    "FILE_MERGE":      "Merge multiple files of any type",
    "FILE_SEARCH":     "Search files by name or content",
    "FILE_BACKUP":     "Backup a file or folder",
    "ZIP_READ":        "Read/extract ZIP archives",
    "ZIP_CREATE":      "Create ZIP archives from folders or files",
    "RECYCLE_BIN":     "Manage recycle bin (list/restore/empty)",
    "SAVE_CONTENT":   "Save previously shown content to a file",
    "CHAT":            "General chat",
}

READ_MODES = ["READ_ONLY", "READ_EXPLAIN"]
DATA_EXTS  = {".csv", ".tsv", ".xlsx"}
