import os
from ..prompts import multi_file_prompt, validation_prompt
from ..llm import call_llm
from ..utils import clean_output, confirm
from ..file_io import write_file
from ..guardrails import run_write_guardrails
from ..content_validator import validate_content


def parse_files(text):
    """Parse FILE: blocks from model output."""
    files   = {}
    current = None
    SKIP    = {"content", "contents", "file content", "file contents",
               "here is the file", "here is the content"}

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")

        if line.strip().upper().startswith("FILE:"):
            current = line.split(":", 1)[1].strip()
            files[current] = []
            continue

        if current is None:
            continue

        if line.strip().lower() in SKIP:
            continue

        files[current].append(line)

    return {k: "\n".join(v).rstrip() for k, v in files.items()}


def handle_existing_file(path):
    """Ask user what to do when a file already exists."""
    if not os.path.exists(path):
        return path

    print(f"\n⚠  File already exists: {path}")
    choice = input(
        "  1 → overwrite\n"
        "  2 → rename\n"
        "  3 → skip\n"
        "  Selection: "
    ).strip()

    if choice == "1":
        return path
    if choice == "2":
        new_name = input("  New filename: ").strip()
        return os.path.join(os.path.dirname(path), new_name)
    return None


def resolve_target_path(path, model_folder=None):
    """Attach folder to bare filename if needed."""
    if os.path.dirname(path):
        return path

    # use model-suggested folder first
    if model_folder and os.path.isdir(model_folder):
        return os.path.join(model_folder, path)

    folder = input(
        f"  No folder specified for '{path}'.\n"
        "  Enter target folder (leave empty for current directory): "
    ).strip()

    return os.path.join(folder, path) if folder else path


def run(filename=None, instructions=None, **kwargs):

    print("  Generating files...")

    prompt     = multi_file_prompt(instructions)
    result     = clean_output(call_llm(prompt))

    # Validation loop
    validation = call_llm(validation_prompt(result))
    attempts   = 0

    while "INVALID" in validation.upper() and attempts < 3:
        print(f"  ⚠  Model output invalid (attempt {attempts+1}), retrying...")
        result     = clean_output(call_llm(prompt))
        validation = call_llm(validation_prompt(result))
        attempts  += 1

    files = parse_files(result)

    if not files:
        print("  Model did not produce any files.")
        return

    # Determine model-suggested base folder from filename field
    model_folder = None
    if filename:
        candidate = filename.strip()
        if os.path.isdir(candidate):
            model_folder = candidate

    print(f"\n{'─'*52}")
    print("  FILES TO BE CREATED")
    print(f"{'─'*52}")
    for f in files:
        print(f"  • {f}")
    print()

    if not confirm("Create these files? (yes/no): "):
        print("Cancelled.")
        return

    for path, content in files.items():

        path = resolve_target_path(path, model_folder)

        # Guardrail
        ok, reason = run_write_guardrails(path)
        if not ok:
            print(f"  Blocked '{path}': {reason}")
            continue

        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            create = input(f"  Folder '{folder}' missing. Create it? (yes/no): ").strip().lower()
            if create not in ("yes", "y"):
                print(f"  Skipping: {path}")
                continue
            os.makedirs(folder, exist_ok=True)

        final_path = handle_existing_file(path)
        if final_path is None:
            continue

        # Strict content validation before write
        ok, reason, clean_content = validate_content(content, final_path)
        if not ok:
            print(f"  ⚠  Content validation failed for '{final_path}': {reason}")
            retry = input("  Write anyway? (yes/no): ").strip().lower()
            if retry not in ("yes", "y"):
                print(f"  Skipped: {final_path}")
                continue
            clean_content = content  # use original if user overrides
        write_file(final_path, clean_content)
        print(f"  ✅ Created: {final_path}  [{reason}]")
