from urllib.parse import urlsplit


def safe_next(next_url: str) -> str:
    """Where to send the user after login: a path on this site, or '/'."""
    if not next_url or next_url != next_url.strip() or any(c in next_url for c in "\\\t\r\n"):
        return "/"
    parts = urlsplit(next_url)
    if parts.scheme or parts.netloc or not next_url.startswith("/") or next_url.startswith("//"):
        return "/"
    return next_url
