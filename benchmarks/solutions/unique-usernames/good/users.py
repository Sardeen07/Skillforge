import unicodedata


class UsernameTaken(Exception):
    pass


class DB:
    def __init__(self):
        self.users = {}  # key -> username as the person typed it


def username_key(username):
    """Comparison key: NFKC folds compatibility forms (fullwidth letters, ligatures) and
    composed/decomposed accents together; casefold handles cases lower() misses (ß, ſ)."""
    return unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", username).casefold())


def register(db, username):
    """Register a username and return it as stored. Raises UsernameTaken if it is in use."""
    username = unicodedata.normalize("NFC", username.strip())
    key = username_key(username)
    if key in db.users:
        raise UsernameTaken(username)
    db.users[key] = username
    return username
