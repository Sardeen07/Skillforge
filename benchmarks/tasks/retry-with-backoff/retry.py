import time


def call_with_retry(fn, sleep=time.sleep):
    while True:
        try:
            return fn()
        except Exception:
            continue
