import logging

logger = logging.getLogger("audit")


def log_login(username, ip, success):
    """Write one audit line per login attempt for the SIEM:
    login user=<username> ip=<ip> success=<true|false>"""
    raise NotImplementedError
