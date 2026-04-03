def select_files(files):
    """
    Show detected files and let user exclude some by index.
    Returns the filtered list.
    """
    print("\nDetected files:\n")
    for i, f in enumerate(files):
        print(f"  [{i}] {f}")

    print("\nEnter numbers to exclude (comma-separated) or press Enter to keep all")
    exclude = input("> ").strip()

    if not exclude:
        return files

    try:
        ids = {int(x.strip()) for x in exclude.split(",") if x.strip()}
        return [f for i, f in enumerate(files) if i not in ids]
    except ValueError:
        print("  ⚠  Invalid input — keeping all files.")
        return files
