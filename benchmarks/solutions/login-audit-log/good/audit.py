import logging

logger = logging.getLogger("audit")


def _clean(value):
    """Escape characters that would let a value forge or split log lines."""
    return str(value).replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def log_login(username, ip, success):
    """Write one audit line per login attempt for the SIEM:
    login user=<username> ip=<ip> success=<true|false>"""
    logger.info("login user=%s ip=%s success=%s", _clean(username), _clean(ip), "true" if success else "false")
