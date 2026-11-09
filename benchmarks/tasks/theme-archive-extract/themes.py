import tarfile
from pathlib import Path


def install_theme(archive_path, themes_dir, name):
    """Unpack an uploaded theme pack (.tar.gz) into themes_dir/name and return that path."""
    dest = Path(themes_dir) / name
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path) as tar:
        tar.extractall(dest)
    return dest
