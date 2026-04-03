from ..file_io import read_file
from ..prompts import explain_prompt
from ..llm import call_llm
from ..resolve import resolve_multi


def run(filename=None, read_mode="READ_ONLY", instructions=None, **kwargs):

    files = resolve_multi(filename, instructions)

    if not files:
        print("No valid files found.")
        return

    last_data = None

    for file_path in files:

        data, err = read_file(file_path)

        if err:
            print(f"Error reading '{file_path}': {err}")
            continue

        last_data = (file_path, data)

        print(f"\n{'─'*52}")
        print(f"  FILE: {file_path}")
        print(f"{'─'*52}\n")

        if hasattr(data, "to_string"):
            print(data.to_string(index=False))
        else:
            print(data)

    # Explain mode — run on last successfully read file
    if read_mode == "READ_EXPLAIN" and last_data:
        file_path, data = last_data

        if hasattr(data, "to_string"):
            data_text = data.to_string(index=False)
        else:
            data_text = str(data)

        print(f"\n{'─'*52}")
        print("  EXPLANATION")
        print(f"{'─'*52}\n")

        explanation = call_llm(explain_prompt(file_path, data_text[:12000]))
        print(explanation)
