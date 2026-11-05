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

import builtins, tempfile


def _files(texts):
    d = Path(tempfile.mkdtemp())
    paths = []
    for n, t in enumerate(texts):
        p = d / f"{n}.log"
        p.write_bytes(t)
        paths.append(str(p))
    return paths


def _tracking():
    opened = []
    real = builtins.open

    def fake(*a, **k):
        f = real(*a, **k)
        opened.append(f)
        return f
    return opened, fake, real


@check("counts")
def _():
    m = load("logscan")
    assert m.count_errors(_files([b"ok\nERROR a\n", b"ERROR b\nERROR c\n"])) == 3


@check("closes-files")
def _():
    m = load("logscan")
    opened, fake, real = _tracking()
    builtins.open = fake
    try:
        m.count_errors(_files([b"ERROR\n"] * 20))
    finally:
        builtins.open = real
    assert opened and all(f.closed for f in opened), f"{sum(not f.closed for f in opened)} files left open"


@check("closes-on-decode-error")
def _():
    m = load("logscan")
    opened, fake, real = _tracking()
    builtins.open = fake
    try:
        try:
            m.count_errors(_files([b"ERROR\n", b"\xff\xfe bad bytes\n"]))
        except UnicodeDecodeError:
            pass
    finally:
        builtins.open = real
    assert opened and all(f.closed for f in opened), "a file stayed open after a decoding error"


if __name__ == "__main__":
    main()
