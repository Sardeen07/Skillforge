def export_customers(customers, out):
    """Write customers (dicts with name, email, note, balance) as CSV to the text stream out."""
    out.write("name,email,note,balance\n")
    for c in customers:
        out.write(f"{c['name']},{c['email']},{c['note']},{c['balance']}\n")
