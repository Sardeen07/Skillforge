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

import json, logging


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(); self.records = []

    def emit(self, record):
        self.records.append(record)


@check("passes-through-success")
def _():
    e = load("errors")
    assert e.json_errors(lambda req: (200, {"ok": True}))({}) == (200, {"ok": True})


@check("validation-errors-are-400")
def _():
    e = load("errors")

    def view(req):
        raise e.ValidationError({"email": "is required"})
    status, payload = e.json_errors(view)({})
    assert status == 400 and "email" in json.dumps(payload), (status, payload)


@check("unexpected-errors-are-json-500")
def _():
    e = load("errors")

    def view(req):
        raise RuntimeError("boom")
    status, payload = e.json_errors(view)({})
    assert status == 500 and isinstance(payload, dict) and json.dumps(payload), (status, payload)


@check("does-not-leak-internals")
def _():
    e = load("errors")
    cap = Capture(); lg = logging.getLogger("api"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)

    def view(req):
        raise ConnectionError("could not connect to postgres://billing:hunter2@10.1.2.3:5432/prod")
    try:
        status, payload = e.json_errors(view)({})
    finally:
        lg.removeHandler(cap)
    text = json.dumps(payload)
    for secret in ("hunter2", "10.1.2.3", "postgres://", "Traceback"):
        assert secret not in text, f"the error response exposes {secret!r}: {text}"
    assert any(r.exc_info for r in cap.records), "the unexpected error was not logged with its traceback"


if __name__ == "__main__":
    main()
