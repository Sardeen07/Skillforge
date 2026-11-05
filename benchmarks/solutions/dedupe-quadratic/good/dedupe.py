def find_duplicate_emails(customers):
    """Emails (lowercased) that appear more than once, in the order they first repeat."""
    seen, dupes = set(), {}
    for c in customers:
        email = c["email"].lower()
        if email in seen:
            dupes.setdefault(email, None)
        else:
            seen.add(email)
    return list(dupes)
