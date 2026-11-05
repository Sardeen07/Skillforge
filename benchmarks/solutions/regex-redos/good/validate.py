import re

NAME = re.compile(r"\w+(?: \w+)*")


def is_valid_display_name(name: str) -> bool:
    return 0 < len(name) <= 40 and NAME.fullmatch(name) is not None
