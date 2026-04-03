"""
bus.py — Agent event bus.

All agent output flows through here so main.py (or a master agent) can
intercept, log, display, or forward every message without touching sys.stdout.

Usage in agent code:
    from .bus import bus
    bus.print("  ✅ File saved")
    bus.info("Classifying task...")
    bus.warn("Row loss detected")
    bus.error("File not found")

Usage in main.py / master agent:
    from agent.bus import bus

    # Option A — default: mirror everything to console (current behaviour)
    bus.set_handler(bus.console_handler)

    # Option B — collect all messages as structured events
    events = []
    bus.set_handler(lambda e: events.append(e))
    start_agent()
    for e in events:
        print(e["level"], e["text"])

    # Option C — both print and collect
    def my_handler(event):
        print(event["text"], end=event.get("end", "\\n"))
        my_log.append(event)
    bus.set_handler(my_handler)
"""

import sys
from datetime import datetime


class AgentBus:
    """
    Lightweight event bus that replaces direct print() calls throughout the agent.
    All output is routed through a single handler that main.py can replace.
    """

    def __init__(self):
        self._handler = self.console_handler
        self._history = []          # rolling buffer of last 500 events
        self._max_history = 500

    # ── Handler management ────────────────────────────────────────────────

    def set_handler(self, fn):
        """
        Replace the output handler.
        fn receives a dict: {level, text, end, timestamp}
        """
        self._handler = fn

    def reset_handler(self):
        """Restore default console output."""
        self._handler = self.console_handler

    # ── Default handler ───────────────────────────────────────────────────

    @staticmethod
    def console_handler(event):
        """Default: print to stdout exactly as before."""
        sys.stdout.write(event["text"] + event.get("end", "\n"))
        sys.stdout.flush()

    # ── Internal emit ─────────────────────────────────────────────────────

    def _emit(self, level, text, end="\n", flush=False):
        event = {
            "level":     level,
            "text":      text,
            "end":       end,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        # Keep rolling history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        try:
            self._handler(event)
        except Exception:
            # Never let a broken handler crash the agent
            sys.stdout.write(text + end)

    # ── Public API — mirrors print() behaviour ────────────────────────────

    def print(self, text="", end="\n", flush=False):
        """Drop-in replacement for print(). Sends level='output'."""
        self._emit("output", str(text), end=end)

    def info(self, text, end="\n"):
        """Informational message (classification, progress, etc.)."""
        self._emit("info", str(text), end=end)

    def success(self, text, end="\n"):
        """Operation succeeded."""
        self._emit("success", str(text), end=end)

    def warn(self, text, end="\n"):
        """Warning — something unexpected but recoverable."""
        self._emit("warning", str(text), end=end)

    def error(self, text, end="\n"):
        """Error — operation failed."""
        self._emit("error", str(text), end=end)

    def prompt(self, text):
        """
        A question being asked to the user (input() call).
        Emitted so a master agent can intercept and answer programmatically.
        """
        self._emit("prompt", str(text), end="")

    # ── History access ────────────────────────────────────────────────────

    def get_history(self, n=None, level=None):
        """
        Return recent events.
        n: limit to last n events.
        level: filter by level ('output','info','success','warning','error','prompt').
        """
        history = self._history
        if level:
            history = [e for e in history if e["level"] == level]
        if n:
            history = history[-n:]
        return history

    def clear_history(self):
        self._history = []

    def last_output(self):
        """Return the last non-empty output text (useful for 'save that as X')."""
        for event in reversed(self._history):
            if event["level"] in ("output", "success") and event["text"].strip():
                return event["text"]
        return None


# Singleton — import this everywhere
bus = AgentBus()
