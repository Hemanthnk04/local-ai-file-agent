from ..file_io import read_file
from ..prompts import rewrite_prompt
from ..llm import call_llm
from ..resolve import resolve_multi
from ..utils import clean_output
from ..diff_tools import show_diff
from ..guardrails import check_content_reduction


def run(filename=None, instructions=None, **kwargs):

    files = resolve_multi(filename, instructions)

    if not files:
        print("  No valid files found.")
        return

    for file_path in files:

        data, err = read_file(file_path)

        if err:
            print(f"  Error reading '{file_path}': {err}")
            continue

        if isinstance(data, pd.DataFrame):
            original_text = data.to_csv(index=False)
        else:
            original_text = str(data)

        print(f"\n{'─'*52}")
        print(f"  DIFF PREVIEW : {file_path}")
        print(f"{'─'*52}\n")

        result = clean_output(call_llm(rewrite_prompt(original_text, instructions, filename=file_path)))

        # Show content-reduction warning even in preview mode
        ok, reason = check_content_reduction(original_text, result, file_path)
        if not ok:
            print(f"{reason}\n")

        show_diff(original_text, result)
        print("\n  (Preview only — file was NOT modified)")
