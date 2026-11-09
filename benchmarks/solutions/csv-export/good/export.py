import csv

FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _cell(value):
    """Text a spreadsheet would run as a formula gets a leading quote (OWASP CSV injection)."""
    if isinstance(value, str) and value.startswith(FORMULA_START):
        return "'" + value
    return value


def export_customers(customers, out):
    """Write customers (dicts with name, email, note, balance) as CSV to the text stream out."""
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["name", "email", "note", "balance"])
    for c in customers:
        writer.writerow([_cell(c["name"]), _cell(c["email"]), _cell(c["note"]), c["balance"]])
