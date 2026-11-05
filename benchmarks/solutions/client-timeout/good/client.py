import json
import socket
import urllib.error
import urllib.request


def fetch_status(url, timeout=5.0):
    """GET url and parse JSON; raise TimeoutError if the server does not answer in time."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise TimeoutError(f"{url} did not answer within {timeout}s") from exc
        raise
    except socket.timeout as exc:
        raise TimeoutError(f"{url} did not answer within {timeout}s") from exc
