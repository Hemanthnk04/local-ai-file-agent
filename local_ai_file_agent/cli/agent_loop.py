import re
import io
import sys

from agent.classifier import classify_task
from agent.tasks import TASK_MAP
from agent.config import TASK_REGISTRY
from agent.utils import confirm
from agent.logger import log
from agent.bus import bus

GUARDRAIL_MESSAGES = {
    "delete_data": (
        "⚠️  GUARDRAIL: This instruction may delete data rows from a file.\n"
        "   The agent will warn you again before writing if rows are lost."
    ),
    "overwrite": (
        "⚠️  GUARDRAIL: This will overwrite an existing file.\n"
        "   A diff will be shown before any changes are saved."
    ),
    "bulk_delete": (
        "🛑 GUARDRAIL: This is a bulk delete operation.\n"
        "   You will be shown a list of files before anything is removed."
    ),
}

# Tasks whose stdout output should be captured and buffered
_OUTPUT_TASKS = {"GENERATE_CODE", "READ_FILE", "CHAT"}

# Patterns that mean the user is pasting inline content → skip classifier
_INLINE_TRIGGER = re.compile(
    r"^(save\s+this|write\s+this|store\s+this|put\s+this|"
    r"save\s+the\s+following|write\s+the\s+following|"
    r"save\s+it\s+as|write\s+it\s+to)\b",
    flags=re.I
)


def _has_file_blocks(text):
    """Return True if input contains FILE: block markers."""
    return bool(re.search(r"^FILE\s*:\s*.+", text, re.I | re.M))


def _has_inline_content(text):
    """Return True if prompt looks like 'save this as X\\n<content>'."""
    lines = text.strip().splitlines()
    return len(lines) >= 2 and bool(_INLINE_TRIGGER.match(lines[0].strip()))


def start_agent():

    bus.print("🧠 Unified File Agent")
    bus.print("Type 'tasks' to list tasks | 'help' for examples | 'exit' to quit\n")

    # Buffer for "save that as X" feature — stores last agent output text
    _last_output = {"content": None, "task": None}

    while True:

        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            bus.print("\nExiting.")
            break

        if not user:
            continue

        lower = user.lower()

        if lower == "exit":
            break

        if lower == "tasks":
            bus.print("\nAvailable Tasks:")
            for k, v in TASK_REGISTRY.items():
                bus.print(f"  {k:20s} — {v}")
            bus.print()
            continue

        if lower == "help":
            bus.print("""
Examples:
  read app.py
  explain config.json
  sort employees.csv by age
  rewrite main.py — add error handling
  create a Flask project scaffold
  generate python code for a binary search tree
  save that as solution.py

  Paste content directly:
    FILE: main.py
    def hello(): print("hi")

  Or inline:
    save this as config.json
    {"host": "localhost", "port": 5432}

  validate data.csv
  convert data.csv to json
  merge sales.csv and customers.csv
  zip the project folder
  what's in archive.zip
  show recycle bin
""")
            continue

        # ── Fast-path: FILE: blocks or inline content → SAVE_CONTENT ──────
        if _has_file_blocks(user) or _has_inline_content(user):
            bus.info("\n  📋 Inline content detected — routing to SAVE_CONTENT")
            bus.print()
            TASK_MAP["SAVE_CONTENT"](
                filename="",
                instructions=user,
                pending_content=_last_output.get("content"),
                raw_user_input=user,
            )
            bus.print()
            continue

        # ── Classify ──────────────────────────────────────────────────────
        bus.info("\n⏳ Classifying...", end="\r")
        intent = classify_task(user)
        task   = intent.pop("task")

        assumed_summary = intent.pop("assumed_summary", "")
        guardrail_flag  = intent.pop("guardrail_flag", "")

        # ── Show interpretation ───────────────────────────────────────────
        bus.info("\n" + "─" * 52)
        bus.info(f"  Task   : {task}  —  {TASK_REGISTRY.get(task, '')}")
        if assumed_summary:
            bus.info(f"  Intent : {assumed_summary}")
        if intent.get("filename"):
            bus.info(f"  File   : {intent['filename']}")
        if intent.get("read_mode"):
            bus.info(f"  Mode   : {intent['read_mode']}")
        if intent.get("instructions"):
            bus.info(f"  Action : {intent['instructions']}")
        bus.info("─" * 52)

        # ── Guardrail warning ─────────────────────────────────────────────
        if guardrail_flag and guardrail_flag in GUARDRAIL_MESSAGES:
            bus.warn("\n" + GUARDRAIL_MESSAGES[guardrail_flag] + "\n")

        # ── Log before confirming ─────────────────────────────────────────
        log.info("classified", task=task,
                 filename=intent.get("filename", ""),
                 summary=assumed_summary[:80])

        # ── Confirm ───────────────────────────────────────────────────────
        if not confirm("Proceed? (yes/no): "):
            log.info("cancelled", task=task)
            bus.print("Cancelled.\n")
            continue

        fn = TASK_MAP.get(task)
        if not fn:
            bus.warn("Unknown task — routing to chat.\n")
            TASK_MAP["CHAT"](instructions=user)
            continue

        bus.print()

        # ── Inject extras for SAVE_CONTENT ────────────────────────────────
        if task == "SAVE_CONTENT":
            intent["pending_content"] = _last_output.get("content")
            intent["raw_user_input"]  = user

        log.task_start(task,
                       filename=intent.get("filename", ""),
                       instructions=str(intent.get("instructions", ""))[:60])
        try:
            if task in _OUTPUT_TASKS:
                # Capture stdout so we can buffer it AND emit through bus
                buf        = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                try:
                    fn(**intent)
                finally:
                    sys.stdout = old_stdout

                captured = buf.getvalue()
                # Emit through bus so master agent sees it
                bus.print(captured, end="")
                _last_output["content"] = captured.strip()
                _last_output["task"]    = task
            else:
                fn(**intent)

            log.task_end(task, status="ok")

        except Exception as e:
            log.error("task_error", task=task, reason=str(e))
            bus.error(f"  ❌ Task error: {e}")

        bus.print()
