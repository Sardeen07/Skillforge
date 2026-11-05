import os


def read_upload(base_dir, name):
    """Return the bytes of the uploaded file `name` stored under base_dir."""
    path = os.path.join(base_dir, name)
    with open(path, "rb") as f:
        return f.read()
