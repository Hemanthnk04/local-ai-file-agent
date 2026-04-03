import os
from ..file_io import read_file
from ..resolve import resolve_single
from ..validation import VALIDATORS

# Extensions where we pass raw data (not string) to the validator
_RAW_DATA_EXTS = {".xlsx", ".docx", ".pdf"}


def run(filename=None, instructions=None, **kwargs):

    path = resolve_single(filename, instructions, prompt_label="file to validate")

    if not path:
        print("  No file specified.")
        return

    data, err = read_file(path)

    if err:
        print(f"  ❌ Error reading '{path}': {err}")
        return

    ext = os.path.splitext(path)[1].lower()

    print(f"\n  Validating : {path}")
    print(f"  Type       : {ext or 'unknown'}")

    validator = VALIDATORS.get(ext)

    if validator:
        # Pass raw data for binary/rich formats; string for everything else
        if ext in _RAW_DATA_EXTS:
            ok, msg = validator(data)
        elif hasattr(data, "to_csv"):
            ok, msg = validator(data.to_csv(index=False))
        elif isinstance(data, list):
            ok, msg = validator("\n".join(str(r) for r in data))
        else:
            ok, msg = validator(str(data))
    else:
        ok, msg = True, f"No specific validator for '{ext}' — file is readable"

    icon = "✅" if ok else "❌"
    print(f"  Result     : {icon} {msg}")

    # Extra info — only show shape/nulls for non-binary tabular files
    # (xlsx validator already reports rows/cols; avoid duplicate for it)
    if hasattr(data, "to_csv") and ext != ".xlsx":
        print(f"  Shape      : {len(data):,} rows × {len(data.columns)} columns")
        null_counts = data.isnull().sum()
        nulls = null_counts[null_counts > 0]
        if not nulls.empty:
            print(f"  Nulls      : {dict(nulls)}")
    elif isinstance(data, str):
        lines = data.splitlines()
        print(f"  Lines      : {len(lines):,}")

    # Show available validators if unsupported
    if ext not in VALIDATORS:
        supported = ", ".join(sorted(VALIDATORS.keys()))
        print(f"\n  ℹ  Validators available for: {supported}")
