import secrets


def new_reset_token() -> str:
    return secrets.token_urlsafe(32)
