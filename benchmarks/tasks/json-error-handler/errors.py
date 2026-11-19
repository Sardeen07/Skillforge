import functools
import logging

logger = logging.getLogger("api")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("invalid request")
        self.errors = errors  # {"field": "message"}


def json_errors(view):
    """Decorator for API views. A view takes a request and returns (status, payload_dict)."""
    return view
