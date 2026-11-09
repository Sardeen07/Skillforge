import random
import time
from email.utils import parsedate_to_datetime

RETRYABLE = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5


class RetryError(Exception):
    pass


def _retry_after(headers):
    """Seconds to wait from a Retry-After header (delta-seconds or HTTP-date), or None."""
    value = {k.lower(): v for k, v in (headers or {}).items()}.get("retry-after")
    if value is None:
        return None
    value = str(value).strip()
    if value.isdigit():
        return float(value)
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def get_with_retry(fetch, url, sleep=time.sleep, base=0.5, cap=60.0):
    """fetch(url) -> (status, headers, body). Returns body on HTTP 200.

    Retries 429 and 5xx at most MAX_ATTEMPTS times in total, waiting what the server asks
    (Retry-After, in either format) or else capped exponential backoff with jitter. Other
    statuses fail immediately: retrying a 4xx cannot help."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        status, headers, body = fetch(url)
        if status == 200:
            return body
        if status not in RETRYABLE:
            raise RetryError(f"{url}: HTTP {status} is not retryable")
        if attempt == MAX_ATTEMPTS:
            raise RetryError(f"{url}: still HTTP {status} after {MAX_ATTEMPTS} attempts")
        wait = _retry_after(headers)
        if wait is None:
            delay = min(cap, base * 2 ** attempt)
            wait = random.uniform(delay / 2, delay)
        sleep(min(wait, cap))
