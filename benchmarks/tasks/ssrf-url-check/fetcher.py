import socket
from urllib.parse import urlsplit


def default_resolve(host):
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


def is_allowed_url(url: str, resolve=default_resolve) -> bool:
    """True if the server may fetch this user-supplied URL."""
    return url.startswith("http")
