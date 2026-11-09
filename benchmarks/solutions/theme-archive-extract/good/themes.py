import os
import tarfile
from pathlib import Path


class UnsafeArchive(Exception):
    pass


def install_theme(archive_path, themes_dir, name):
    """Unpack an uploaded theme pack (.tar.gz) into themes_dir/name and return that path.

    Only regular files and directories are extracted, and only to paths inside the theme
    folder: '..' and absolute names are refused, and so are symlinks and hard links, which
    could otherwise point a later member outside the folder."""
    dest = Path(themes_dir) / name
    dest.mkdir(parents=True, exist_ok=True)
    root = os.path.realpath(dest)
    with tarfile.open(archive_path) as tar:
        members = tar.getmembers()
        for m in members:
            if not (m.isfile() or m.isdir()):
                raise UnsafeArchive(f"{m.name}: links and special files are not allowed")
            target = os.path.realpath(os.path.join(root, m.name))
            if os.path.commonpath([root, target]) != root:
                raise UnsafeArchive(f"{m.name}: outside the theme folder")
        for m in members:
            m.mode = (m.mode | 0o600) & 0o755
            tar.extract(m, root)
    return dest
