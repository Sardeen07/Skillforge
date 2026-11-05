import json
import urllib.request


def fetch_status(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())
