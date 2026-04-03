def confirm(msg):
    """Ask yes/no question. Returns True if user answers yes/y."""
    return input(msg).strip().lower() in ["yes", "y"]


def clean_output(text):
    """Strip markdown fences and trailing whitespace from LLM output."""
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines)
