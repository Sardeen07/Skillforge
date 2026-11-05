def find_duplicate_emails(customers):
    """Emails (lowercased) that appear more than once, in the order they first repeat."""
    seen, dupes = [], []
    for c in customers:
        email = c["email"].lower()
        if email in seen:
            if email not in dupes:
                dupes.append(email)
        else:
            seen.append(email)
    return dupes
