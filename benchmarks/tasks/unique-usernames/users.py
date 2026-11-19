class UsernameTaken(Exception):
    pass


class DB:
    def __init__(self):
        self.users = {}  # key -> username as the person typed it


def register(db, username):
    """Register a username and return it as stored. Raises UsernameTaken if it is in use."""
    username = username.strip()
    if username in db.users:
        raise UsernameTaken(username)
    db.users[username] = username
    return username
