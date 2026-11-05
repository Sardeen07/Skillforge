import random
import time

TRANSIENT = (ConnectionError, TimeoutError)


def call_with_retry(fn, sleep=time.sleep, attempts=4, base=0.2, cap=5.0):
    """Call fn, retrying transient failures with capped exponential backoff and full jitter."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except TRANSIENT:
            if attempt == attempts:
                raise
            delay = min(cap, base * 2 ** attempt)
            sleep(random.uniform(delay / 2, delay))
