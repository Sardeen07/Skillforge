import functools
import logging
import uuid

logger = logging.getLogger("api")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("invalid request")
        self.errors = errors  # {"field": "message"}


def json_errors(view):
    """Decorator for API views. A view takes a request and returns (status, payload_dict).

    Expected errors become 400 responses with their field errors. Anything else becomes a
    generic 500 with a request id; the exception and traceback go to the log only, never
    to the client (messages can contain credentials, SQL, hostnames)."""
    @functools.wraps(view)
    def wrapper(request):
        try:
            return view(request)
        except ValidationError as exc:
            return 400, {"error": "validation_failed", "fields": exc.errors}
        except Exception:
            request_id = uuid.uuid4().hex[:12]
            logger.exception("unhandled error in %s (request %s)", view.__name__, request_id)
            return 500, {"error": "internal_error", "request_id": request_id}
    return wrapper
