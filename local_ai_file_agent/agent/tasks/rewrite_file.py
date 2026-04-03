import os
from ..file_io import read_file, write_file
from ..prompts import rewrite_prompt, validation_prompt
from ..llm import call_llm
from ..chunker import warn_if_large, chunk_rewrite
from ..resolve import resolve_multi
from ..utils import confirm, clean_output
from ..diff_tools import show_diff
from ..guardrails import check_content_reduction, run_write_guardrails
from ..content_validator import validate_content
from ..config import DATA_EXTS, AUTO_BACKUP, SHOW_DIFF
from .file_backup import backup_silently


def _count_data_rows(text):
    """Count non-header, non-empty lines — meaningful for tabular data."""
    lines = [l for l in text.splitlines() if l.strip()]
    return max(0, len(lines) - 1)


def run(filename=None, instructions=None, **kwargs):

    files = resolve_multi(filename, instructions)

    if not files:
        print("  No valid files found.")
        return

    for file_path in files:

        ext = os.path.splitext(file_path)[1].lower()

        # ── Read ──────────────────────────────────────────────────────────
        data, err = read_file(file_path)
        if err:
            print(f"  Error reading '{file_path}': {err}")
            continue

        original_text = data.to_csv(index=False) if hasattr(data, "to_csv") else str(data)
        row_count     = _count_data_rows(original_text) if ext in DATA_EXTS else 0

        # ── Auto-backup (respects config) ─────────────────────────────────
        if AUTO_BACKUP:
            bk = backup_silently(file_path)
            if bk:
                print(f"  💾 Backup : {bk}")

        print(f"\n{'─'*52}")
        print(f"  REWRITING : {file_path}")
        if row_count:
            print(f"  Original  : {row_count} data rows")
        print(f"{'─'*52}\n")

        # ── Pre-write guardrail ───────────────────────────────────────────
        ok, reason = run_write_guardrails(file_path)
        if not ok:
            print(f"  Blocked: {reason}")
            continue

        # ── Context window check ──────────────────────────────────────────
        warn_if_large(original_text, os.path.basename(file_path))

        # ── Generate rewrite (chunk_rewrite handles large files) ──────────
        def _do_rewrite(chunk_text):
            p = rewrite_prompt(
                chunk_text, instructions,
                row_count=row_count if row_count else None,
                filename=file_path,
            )
            return clean_output(call_llm(p, show_progress=True))

        result = chunk_rewrite(original_text, _do_rewrite, file_path)
        if not result:
            print("  ❌ Rewrite failed — no output from model.")
            continue

        # ── Validation loop — retry up to 3 times ────────────────────────
        attempts = 0
        while attempts < 3:
            validation = call_llm(validation_prompt(result))
            if "INVALID" not in validation.upper():
                break
            attempts += 1
            print(f"  ⚠  Model output invalid (attempt {attempts}), retrying...")
            result = clean_output(_do_rewrite(original_text))

        if "INVALID" in call_llm(validation_prompt(result)).upper():
            print("  Model could not produce valid output after 3 attempts. Aborting.")
            continue

        # ── Content-reduction guardrail ───────────────────────────────────
        content_ok, content_reason = check_content_reduction(original_text, result, file_path)
        if not content_ok:
            print(f"\n{content_reason}")
            label = "data" if ext in DATA_EXTS else "code"
            if not confirm(f"  Model reduced {label} content. Proceed anyway? (yes/no): "):
                print(f"  Skipped: {file_path}")
                continue

        # ── Show diff (respects config) ───────────────────────────────────
        if SHOW_DIFF:
            print("\n--- PROPOSED CHANGES ---\n")
            show_diff(original_text, result,
                      fromfile=os.path.basename(file_path) + " (original)",
                      tofile=os.path.basename(file_path) + " (rewritten)")

        if not confirm(f"\nApply changes to '{file_path}'? (yes/no): "):
            print(f"  Skipped: {file_path}")
            continue

        # ── Strict content validation before write ────────────────────────
        val_ok, val_reason, clean_result = validate_content(result, file_path)
        if not val_ok:
            print(f"  ⚠  Content validation: {val_reason}")
            if not confirm("  Apply anyway? (yes/no): "):
                print(f"  Skipped: {file_path}")
                continue
            clean_result = result

        write_file(file_path, clean_result)
        print(f"  ✅ Saved: {file_path}  [{val_reason}]")
