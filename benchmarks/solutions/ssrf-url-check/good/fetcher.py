import ipaddress
import socket
from urllib.parse import urlsplit


def default_resolve(host):
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


def _public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return addr.is_global and not addr.is_multicast


def is_allowed_url(url: str, resolve=default_resolve) -> bool:
    """True if the server may fetch this user-supplied URL. Callers must connect to an
    address that passed this check (not re-resolve), or DNS rebinding can bypass it."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    try:
        ips = [parts.hostname] if _is_ip(parts.hostname) else resolve(parts.hostname)
        return bool(ips) and all(_public(ip) for ip in ips)
    except (OSError, ValueError, KeyError):
        return False


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
