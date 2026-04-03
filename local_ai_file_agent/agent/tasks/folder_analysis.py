import os

from ..folder_ops import scan_folder
from ..selection import select_files
from ..llm import call_llm
from ..file_io import read_file
from ..prompts import folder_analysis_prompt
from ..config import MAX_FILE_CHARS


# Each file gets at most this many chars in the combined prompt
# to stay gentle on RAM — capped at half the global limit
_PER_FILE_LIMIT = min(4000, MAX_FILE_CHARS // 4)


def run(filename=None, instructions=None, **kwargs):

    # Resolve folder
    path = ""
    if filename:
        candidate = filename.strip()
        if os.path.isdir(candidate):
            path = candidate

    if not path:
        path = input("Enter folder path (leave empty for current directory): ").strip()
    if not path:
        path = os.getcwd()

    if not os.path.isdir(path):
        print(f"  Folder not found: {path}")
        retry = input("  Provide valid folder path: ").strip()
        if not os.path.isdir(retry):
            print("  Still not found. Aborting.")
            return
        path = retry

    print(f"\n  Scanning: {path}")
    files = scan_folder(path)

    if not files:
        print("  No files detected.")
        return

    selected = select_files(files)
    if not selected:
        print("  No files selected.")
        return

    contents = []

    for f in selected:
        data, err = read_file(f)
        if err:
            continue

        # Normalise to string without heavy imports
        if hasattr(data, "to_string"):          # DataFrame
            file_text = data.to_string(index=False)
        elif isinstance(data, list):
            file_text = "\n".join(str(row) for row in data)
        else:
            file_text = str(data)

        if not file_text.strip():
            continue

        if len(file_text) > _PER_FILE_LIMIT:
            file_text = file_text[:_PER_FILE_LIMIT] + f"\n... [truncated at {_PER_FILE_LIMIT} chars]"

        contents.append(f"\nFILE: {f}\n{file_text}")

    if not contents:
        print("  No readable file contents.")
        return

    # Total prompt guard — cap combined content
    combined = "".join(contents)
    if len(combined) > MAX_FILE_CHARS:
        combined = combined[:MAX_FILE_CHARS] + "\n... [total content truncated]"
        print(f"  ⚠  Combined content truncated to {MAX_FILE_CHARS:,} chars for model.")

    print(f"\n  Analysing {len(contents)} file(s)...\n")

    prompt = folder_analysis_prompt(combined, instructions or "Explain structure and functionality.")
    result = call_llm(prompt, show_progress=True)

    print(f"{'─'*52}")
    print("  ANALYSIS")
    print(f"{'─'*52}\n")
    print(result)
