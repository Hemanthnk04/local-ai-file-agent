"""
agent_api.py — programmatic API for master agent / external integration.

A master agent can import this instead of running the CLI loop.
Supports JSON-in / JSON-out for clean inter-agent communication.

Usage from a master agent:
    from agent.agent_api import FileAgentAPI
    api = FileAgentAPI()

    # Run any task
    result = api.run(task="REWRITE_FILE",
                     filename="data.csv",
                     instructions="sort by age column")

    # Or let it classify automatically
    result = api.execute("sort data.csv by age")

    print(result["status"])   # "ok" | "error" | "blocked"
    print(result["message"])  # human-readable summary
    print(result["data"])     # task-specific output data
"""

import traceback
from .classifier import classify_task
from .tasks import TASK_MAP
from .config import TASK_REGISTRY
from .logger import log
from .content_validator import validate_content


class FileAgentAPI:
    """
    Programmatic interface to the file agent.
    All methods return structured dicts — no interactive prompts.
    Set interactive=False to suppress all input() calls (for master agent use).
    """

    def __init__(self, interactive=True):
        self.interactive = interactive

    def capabilities(self):
        """Return agent capabilities as structured dict."""
        return {
            "status": "ok",
            "tasks":  {k: v for k, v in TASK_REGISTRY.items()},
            "version": "1.0",
            "interactive": self.interactive,
        }

    def classify(self, user_input):
        """
        Classify a natural-language prompt.
        Returns the classifier JSON dict.
        """
        try:
            result = classify_task(user_input)
            return {"status": "ok", "classification": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run(self, task, filename="", instructions="", read_mode="", **kwargs):
        """
        Run a specific task by name.
        Returns structured result dict.
        """
        if task not in TASK_MAP:
            return {
                "status":  "error",
                "message": f"Unknown task: '{task}'. Valid tasks: {sorted(TASK_MAP.keys())}",
                "data":    None,
            }

        fn = TASK_MAP[task]
        log.task_start(task, filename=filename, instructions=instructions[:80])

        try:
            fn(filename=filename, instructions=instructions,
               read_mode=read_mode, **kwargs)

            log.task_end(task, status="ok")
            return {
                "status":  "ok",
                "task":    task,
                "message": f"Task '{task}' completed successfully.",
                "data":    None,
            }

        except SystemExit:
            return {"status": "cancelled", "task": task, "message": "Cancelled by user."}
        except Exception as e:
            log.error("task_exception", task=task, reason=str(e))
            return {
                "status":  "error",
                "task":    task,
                "message": str(e),
                "data":    traceback.format_exc(),
            }

    def execute(self, user_input):
        """
        Full pipeline: classify → run → return result.
        Drop-in for master agent use.
        """
        clf = self.classify(user_input)
        if clf["status"] != "ok":
            return clf

        c    = clf["classification"]
        task = c.get("task", "CHAT")

        return self.run(
            task=task,
            filename=c.get("filename", ""),
            instructions=c.get("instructions", user_input),
            read_mode=c.get("read_mode", ""),
        )

    def validate_file_content(self, content, filename):
        """
        Validate content for a given filename before writing.
        Returns (ok, reason, cleaned_content).
        Useful for master agents that generate content externally.
        """
        return validate_content(content, filename)

    def health(self):
        """Quick health check — returns ok if the agent can import its deps."""
        checks = {}
        deps = [
            ("pandas",    "import pandas"),
            ("openpyxl",  "import openpyxl"),
            ("pypdf",     "from pypdf import PdfReader"),
            ("docx",      "from docx import Document"),
            ("reportlab", "from reportlab.pdfgen import canvas"),
            ("yaml",      "import yaml"),
        ]
        for name, stmt in deps:
            try:
                exec(stmt)
                checks[name] = "ok"
            except ImportError:
                checks[name] = "missing"

        all_ok = all(v == "ok" for v in checks.values())
        return {
            "status":       "ok" if all_ok else "degraded",
            "dependencies": checks,
            "tasks":        len(TASK_MAP),
        }
