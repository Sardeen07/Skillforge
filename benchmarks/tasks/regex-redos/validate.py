import re

NAME = re.compile(r"^(\w+\s?)*$")


def is_valid_display_name(name: str) -> bool:
    return len(name) <= 40 and bool(NAME.match(name)) and name.strip() == name and name != ""
