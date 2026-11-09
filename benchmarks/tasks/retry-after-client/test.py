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

import email.utils


class Fake:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def __call__(self, url):
        self.calls += 1
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


def _error(c):
    return getattr(c, "RetryError", Exception)


@check("recovers-from-transient-errors")
def _():
    c = load("client"); f = Fake([(503, {}, b""), (503, {}, b""), (200, {}, b"ok")])
    assert c.get_with_retry(f, "u", sleep=lambda s: None) == b"ok" and f.calls == 3


@check("gives-up-after-5-attempts")
def _():
    c = load("client"); f = Fake([(503, {}, b"")])
    try:
        c.get_with_retry(f, "u", sleep=lambda s: None)
    except _error(c):
        assert f.calls == 5, f"{f.calls} attempts"
        return
    raise AssertionError("no RetryError")


@check("no-retry-on-other-4xx")
def _():
    c = load("client"); f = Fake([(404, {}, b"")])
    try:
        c.get_with_retry(f, "u", sleep=lambda s: None)
    except Exception:
        assert f.calls == 1, f"retried a 404 {f.calls - 1} times"
        return
    raise AssertionError("404 did not raise")


@check("honors-retry-after-seconds")
def _():
    c = load("client"); waits = []
    f = Fake([(429, {"Retry-After": "7"}, b""), (200, {}, b"ok")])
    c.get_with_retry(f, "u", sleep=waits.append)
    assert waits and waits[0] >= 7, f"waited {waits} when the server asked for 7s"


@check("honors-retry-after-http-date")
def _():
    c = load("client"); waits = []
    when = email.utils.formatdate(time.time() + 30, usegmt=True)
    f = Fake([(503, {"Retry-After": when}, b""), (200, {}, b"ok")])
    c.get_with_retry(f, "u", sleep=waits.append)
    assert waits and waits[0] >= 25, f"waited {waits} when the server asked to come back in 30s ({when})"


@check("backs-off-without-header")
def _():
    c = load("client"); runs = []
    for _ in range(30):
        waits = []
        try:
            c.get_with_retry(Fake([(503, {}, b"")]), "u", sleep=waits.append)
        except Exception:
            pass
        runs.append(waits)
    assert all(len(w) == 4 for w in runs), [len(w) for w in runs][:3]
    mean = lambda i: sum(w[i] for w in runs) / len(runs)
    assert mean(3) > 2 * mean(0), f"mean waits {[round(mean(i), 2) for i in range(4)]}: not backing off"


if __name__ == "__main__":
    main()
