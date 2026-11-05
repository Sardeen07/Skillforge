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

import tempfile


def _setup():
    root = Path(tempfile.mkdtemp())
    (root / "uploads").mkdir()
    (root / "uploads" / "report.txt").write_bytes(b"ok")
    (root / "uploads" / "sub").mkdir()
    (root / "uploads" / "sub" / "a.txt").write_bytes(b"nested")
    (root / "secrets.env").write_bytes(b"TOKEN=1")
    return root


@check("reads-normal-files")
def _():
    f = load("files"); root = _setup()
    assert f.read_upload(str(root / "uploads"), "report.txt") == b"ok"
    assert f.read_upload(str(root / "uploads"), "sub/a.txt") == b"nested"


@check("blocks-dotdot")
def _():
    f = load("files"); root = _setup()
    for name in ("../secrets.env", "sub/../../secrets.env"):
        try:
            data = f.read_upload(str(root / "uploads"), name)
        except PermissionError:
            continue
        raise AssertionError(f"{name} returned {data!r}")


@check("blocks-absolute")
def _():
    f = load("files"); root = _setup()
    try:
        data = f.read_upload(str(root / "uploads"), str(root / "secrets.env"))
    except PermissionError:
        return
    raise AssertionError(f"absolute path returned {data!r}")


@check("blocks-prefix-sibling")
def _():
    f = load("files"); root = _setup()
    (root / "uploads-old").mkdir()
    (root / "uploads-old" / "x.txt").write_bytes(b"sibling")
    try:
        data = f.read_upload(str(root / "uploads"), "../uploads-old/x.txt")
    except PermissionError:
        return
    raise AssertionError(f"sibling directory with the same prefix returned {data!r}")


if __name__ == "__main__":
    main()
