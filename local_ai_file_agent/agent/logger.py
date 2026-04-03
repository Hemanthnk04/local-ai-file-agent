"""
logger.py — lightweight structured logging for the file agent.

Writes JSON lines to .agent_logs/agent.log so a master agent
can parse the event stream. Also prints human-readable output to console.

Usage:
    from .logger import log
    log.info("task_started", task="REWRITE_FILE", file="data.csv")
    log.success("file_written", file="data.csv", size=1024)
    log.warning("row_loss", original=100, new=60)
    log.error("read_failed", file="x.csv", reason="not found")
"""

import os
import json
import sys
from datetime import datetime
from .config import BASE_DIR

LOG_DIR  = os.path.join(BASE_DIR, ".agent_logs")
LOG_FILE = os.path.join(LOG_DIR, "agent.log")

# ANSI colours (disabled on Windows if not supported)
_USE_COLOUR = sys.stdout.isatty() and os.name != "nt" or os.environ.get("FORCE_COLOR")
_C = {
    "reset":   "\033[0m"  if _USE_COLOUR else "",
    "info":    "\033[36m" if _USE_COLOUR else "",   # cyan
    "success": "\033[32m" if _USE_COLOUR else "",   # green
    "warning": "\033[33m" if _USE_COLOUR else "",   # yellow
    "error":   "\033[31m" if _USE_COLOUR else "",   # red
    "debug":   "\033[90m" if _USE_COLOUR else "",   # grey
}


class AgentLogger:
    def __init__(self):
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _write(self, level, event, **kwargs):
        os.makedirs(LOG_DIR, exist_ok=True)
        record = {
            "ts":      datetime.now().isoformat(timespec="seconds"),
            "session": self._session_id,
            "level":   level,
            "event":   event,
            **kwargs,
        }
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass   # never crash the agent over logging

    def _console(self, level, event, **kwargs):
        colour  = _C.get(level, "")
        reset   = _C["reset"]
        ts      = datetime.now().strftime("%H:%M:%S")
        details = "  ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        prefix  = {"info":"ℹ","success":"✅","warning":"⚠","error":"❌","debug":"·"}.get(level, "•")
        line    = f"{colour}{prefix} [{ts}] {event}{reset}"
        if details:
            line += f"  {_C['debug']}{details}{reset}"
        # Only print warnings/errors/success to console; suppress debug in normal mode
        if level in ("success", "warning", "error"):
            print(f"  {line}")

    def info(self, event, **kwargs):
        self._write("info", event, **kwargs)

    def success(self, event, **kwargs):
        self._write("success", event, **kwargs)
        self._console("success", event, **kwargs)

    def warning(self, event, **kwargs):
        self._write("warning", event, **kwargs)
        self._console("warning", event, **kwargs)

    def error(self, event, **kwargs):
        self._write("error", event, **kwargs)
        self._console("error", event, **kwargs)

    def debug(self, event, **kwargs):
        self._write("debug", event, **kwargs)

    def task_start(self, task, **kwargs):
        self._write("info", "task_start", task=task, **kwargs)

    def task_end(self, task, status="ok", **kwargs):
        self._write("info", "task_end", task=task, status=status, **kwargs)

    # ── Master-agent integration ───────────────────────────────────────────
    def get_recent(self, n=50):
        """Return last n log entries as list of dicts — for master agent polling."""
        if not os.path.exists(LOG_FILE):
            return []
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            records = []
            for line in lines[-n:]:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
            return records
        except Exception:
            return []


log = AgentLogger()
