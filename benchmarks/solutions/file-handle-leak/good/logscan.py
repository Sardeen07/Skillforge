def count_errors(paths):
    """Total number of lines containing 'ERROR' across the files (UTF-8)."""
    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            total += sum(1 for line in f if "ERROR" in line)
    return total
