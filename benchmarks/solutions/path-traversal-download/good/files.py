import os


def read_upload(base_dir, name):
    """Return the bytes of the uploaded file `name` stored under base_dir."""
    base = os.path.realpath(base_dir)
    path = os.path.realpath(os.path.join(base, name))
    if os.path.commonpath([base, path]) != base:
        raise PermissionError(f"{name!r} is outside the upload directory")
    with open(path, "rb") as f:
        return f.read()
