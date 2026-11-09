import time


def get_with_retry(fetch, url, sleep=time.sleep):
    """fetch(url) -> (status, headers, body). Returns body on HTTP 200."""
    while True:
        status, headers, body = fetch(url)
        if status == 200:
            return body
        sleep(1)
