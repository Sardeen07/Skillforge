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

import logging


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(); self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def _logged(a, *args):
    cap = Capture(); lg = logging.getLogger("audit"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)
    try:
        a.log_login(*args)
    finally:
        lg.removeHandler(cap)
    return cap.lines


@check("writes-the-format")
def _():
    a = load("audit")
    assert _logged(a, "ann", "10.0.0.5", True) == ["login user=ann ip=10.0.0.5 success=true"]
    assert _logged(a, "bob", "10.0.0.6", False) == ["login user=bob ip=10.0.0.6 success=false"]


@check("cannot-forge-lines")
def _():
    a = load("audit")
    for evil in ("eve\nlogin user=admin ip=10.0.0.1 success=true", "eve\r\nlogin user=admin ip=10.0.0.1 success=true"):
        lines = _logged(a, evil, "203.0.113.9", False)
        assert len(lines) == 1, lines
        assert "\n" not in lines[0] and "\r" not in lines[0], f"a username split the audit line: {lines[0]!r}"
        assert "eve" in lines[0], "the username was dropped instead of escaped"


if __name__ == "__main__":
    main()
