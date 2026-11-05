import base64
import pickle

SECRET = b"rotate-me"


def dump_session(data: dict) -> str:
    return base64.urlsafe_b64encode(pickle.dumps(data)).decode()


def load_session(cookie: str):
    try:
        return pickle.loads(base64.urlsafe_b64decode(cookie))
    except Exception:
        return None
