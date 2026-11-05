import random
import string

ALPHABET = string.ascii_letters + string.digits


def new_reset_token() -> str:
    return "".join(random.choice(ALPHABET) for _ in range(16))
