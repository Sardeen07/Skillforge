"""Hidden test. Not shown to the agent. Run after the arm finishes.

Prints PASS/FAIL per check and SCORE: n/m; exits 0 only on a full score. Each check runs
with a time limit, so a hang counts as a failure instead of stalling the run.
"""
GRADER_VERSION = 1
import importlib, os, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CHECKS = []


def check(name, timeout=20):
    def register(fn):
        CHECKS.append((name, fn, timeout))
        return fn
    return register


def load(module):
    """A fresh import of the module the agent edited."""
    sys.modules.pop(module, None)
    return importlib.import_module(module)


def main():
    print("GRADER: behavioral")
    passed = 0
    for name, fn, timeout in CHECKS:
        result = {}

        def run():
            try:
                fn()
                result["ok"] = True
            except BaseException as exc:  # noqa: BLE001 - every failure is a FAIL line
                result["error"] = f"{type(exc).__name__}: {exc}"[:300]

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            result["error"] = f"timed out after {timeout}s"
        if result.get("ok"):
            passed += 1
            print(f"PASS {name}")
        else:
            print(f"FAIL {name} {result.get('error')}")
    print(f"SCORE: {passed}/{len(CHECKS)}")
    sys.stdout.flush()
    os._exit(0 if passed == len(CHECKS) else 1)

import io, tarfile, tempfile


def _tar(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for e in entries:
            info = tarfile.TarInfo(e["name"])
            if e.get("symlink"):
                info.type, info.linkname = tarfile.SYMTYPE, e["symlink"]
                tar.addfile(info)
            elif e.get("dir"):
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            else:
                data = e.get("data", b"x")
                info.size, info.mode = len(data), 0o644
                tar.addfile(info, io.BytesIO(data))


def _install(t, entries):
    root = Path(tempfile.mkdtemp())
    (root / "themes").mkdir()
    secret = root / "secret.txt"; secret.write_bytes(b"original")
    archive = root / "upload.tar.gz"
    _tar(archive, [{**e, "symlink": e["symlink"].replace("ROOT", str(root))} if e.get("symlink") else e for e in entries])
    try:
        t.install_theme(str(archive), str(root / "themes"), "dark")
    except Exception:
        pass
    return root, secret


@check("installs-normal-theme")
def _():
    t = load("themes"); root = Path(tempfile.mkdtemp()); archive = root / "a.tar.gz"
    _tar(archive, [{"name": "css", "dir": True}, {"name": "css/site.css", "data": b"body{}"}, {"name": "theme.json", "data": b"{}"}])
    dest = Path(t.install_theme(str(archive), str(root / "themes"), "dark"))
    assert (dest / "css/site.css").read_bytes() == b"body{}" and (dest / "theme.json").exists()


@check("blocks-dotdot-and-absolute-names")
def _():
    t = load("themes")
    root, secret = _install(t, [{"name": "../../secret.txt", "data": b"pwned"}])
    assert secret.read_bytes() == b"original", "'..' member overwrote a file"
    root, secret = _install(t, [{"name": "ok.txt", "data": b"x"}])
    abs_target = root / "abs.txt"
    root2, _ = _install(t, [{"name": str(abs_target), "data": b"pwned"}])
    assert not abs_target.exists(), "absolute member path written"


@check("blocks-symlink-escape")
def _():
    t = load("themes")
    root, secret = _install(t, [{"name": "link", "symlink": "ROOT"}, {"name": "link/secret.txt", "data": b"pwned"}])
    assert secret.read_bytes() == b"original", "wrote through a symlink to outside the theme folder"
    leaked = [p for p in (root / "themes").rglob("*") if p.is_symlink() and not str(os.path.realpath(p)).startswith(str(os.path.realpath(root / "themes")))]
    assert not leaked, f"symlink pointing outside created: {leaked}"


if __name__ == "__main__":
    main()
