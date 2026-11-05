def count_errors(paths):
    """Total number of lines containing 'ERROR' across the files (UTF-8)."""
    total = 0
    for path in paths:
        f = open(path, encoding="utf-8")
        for line in f:
            if "ERROR" in line:
                total += 1
    return total
