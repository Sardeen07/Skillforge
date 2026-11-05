def safe_next(next_url: str) -> str:
    """Where to send the user after login."""
    return next_url or "/"
