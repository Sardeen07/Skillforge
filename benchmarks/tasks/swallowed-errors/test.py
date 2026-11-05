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
        super().__init__(); self.records = []

    def emit(self, record):
        self.records.append(record)


def _push(fail_ids, interrupt_id=None):
    pushed = []

    def push(c):
        if c["id"] == interrupt_id:
            raise KeyboardInterrupt
        if c["id"] in fail_ids:
            raise ConnectionError(f"crm down for {c['id']}")
        pushed.append(c["id"])
    return push, pushed


@check("continues-and-reports")
def _():
    s = load("sync")
    push, pushed = _push({2, 4})
    failed = s.sync_contacts([{"id": i} for i in range(1, 6)], push)
    assert pushed == [1, 3, 5] and sorted(failed) == [2, 4], (pushed, failed)


@check("logs-with-traceback")
def _():
    s = load("sync")
    cap = Capture(); s.logger.addHandler(cap); s.logger.setLevel(logging.DEBUG)
    try:
        push, _ = _push({2})
        s.sync_contacts([{"id": 1}, {"id": 2}], push)
    finally:
        s.logger.removeHandler(cap)
    errors = [r for r in cap.records if r.levelno >= logging.ERROR]
    assert errors and errors[0].exc_info, "failure not logged with its traceback"


@check("keyboard-interrupt-stops")
def _():
    s = load("sync")
    push, pushed = _push(set(), interrupt_id=2)
    try:
        s.sync_contacts([{"id": i} for i in range(1, 6)], push)
    except KeyboardInterrupt:
        assert pushed == [1]
        return
    raise AssertionError("KeyboardInterrupt was swallowed")


if __name__ == "__main__":
    main()
