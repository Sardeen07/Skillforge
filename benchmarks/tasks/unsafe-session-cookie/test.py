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

import base64, json, pickle


class Boom:
    def __reduce__(self):
        return (exec, ("import os; os.environ['SF_PWNED'] = '1'",))


@check("round-trip")
def _():
    s = load("sessions")
    c = s.dump_session({"user_id": 7, "cart": [1, 2]})
    assert s.load_session(c) == {"user_id": 7, "cart": [1, 2]}


@check("no-code-execution")
def _():
    s = load("sessions")
    os.environ.pop("SF_PWNED", None)
    evil = base64.urlsafe_b64encode(pickle.dumps(Boom())).decode()
    s.load_session(evil)
    assert "SF_PWNED" not in os.environ, "loading a crafted cookie executed code"


@check("rejects-tampering")
def _():
    s = load("sessions")
    c = s.dump_session({"user_id": 7})
    forged = [base64.urlsafe_b64encode(json.dumps({"user_id": 1}).encode()).decode(),
              c.replace("7", "1"), c[:-2] + ("AA" if not c.endswith("AA") else "BB")]
    for f in forged:
        got = s.load_session(f)
        assert got is None or got.get("user_id") == 7 and f == c, (f, got)


if __name__ == "__main__":
    main()
