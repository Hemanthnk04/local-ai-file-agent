import difflib

MAX_DIFF_LINES = 80   # truncate very large diffs to avoid flooding terminal


def show_diff(old, new, fromfile="original", tofile="rewritten"):
    """
    Print a unified diff between old and new text.
    Truncates output if diff is very large.
    """
    diff = list(difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=fromfile,
        tofile=tofile,
        lineterm="",
    ))

    if not diff:
        print("  (no changes detected)")
        return

    if len(diff) > MAX_DIFF_LINES:
        for line in diff[:MAX_DIFF_LINES]:
            print(line)
        print(f"\n  ... [{len(diff) - MAX_DIFF_LINES} more diff lines truncated]")
    else:
        print("\n".join(diff))
