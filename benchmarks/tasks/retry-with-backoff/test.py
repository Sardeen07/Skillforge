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

class Flaky:
    def __init__(self, failures, exc=ConnectionError):
        self.failures, self.exc, self.calls = failures, exc, 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc(f"attempt {self.calls}")
        return "ok"


@check("retries-transient")
def _():
    r = load("retry"); waits = []
    f = Flaky(2)
    assert r.call_with_retry(f, sleep=waits.append) == "ok" and f.calls == 3
    f = Flaky(2, TimeoutError)
    assert r.call_with_retry(f, sleep=waits.append) == "ok"


@check("no-retry-on-permanent")
def _():
    r = load("retry"); waits = []
    f = Flaky(5, ValueError)
    try:
        r.call_with_retry(f, sleep=waits.append)
    except ValueError:
        assert f.calls == 1, f"retried a permanent error {f.calls - 1} times"
        return
    raise AssertionError("ValueError was swallowed")


@check("gives-up-after-4")
def _():
    r = load("retry"); waits = []
    f = Flaky(100)
    try:
        r.call_with_retry(f, sleep=waits.append)
    except ConnectionError as e:
        assert f.calls == 4, f"{f.calls} attempts"
        assert "attempt 4" in str(e), "did not re-raise the last error"
        return
    raise AssertionError("did not raise after giving up")


@check("exponential-backoff-with-jitter")
def _():
    r = load("retry")
    runs = []
    for _ in range(40):
        waits = []
        try:
            r.call_with_retry(Flaky(100), sleep=waits.append)
        except ConnectionError:
            pass
        runs.append(waits)
    for waits in runs:
        assert len(waits) == 3, f"slept {len(waits)} times between 4 attempts"
        assert all(w >= 0 for w in waits), waits
    # Any jitter scheme (full, equal, decorrelated) still grows on average: compare means
    # over many runs, never one run, where full jitter can legitimately shrink a wait.
    mean = lambda i: sum(w[i] for w in runs) / len(runs)
    assert mean(2) > 1.5 * mean(0), f"mean waits {mean(0):.3f}, {mean(1):.3f}, {mean(2):.3f}: not exponential"
    assert len({tuple(w) for w in runs}) > 1, "no jitter: every run waited exactly the same"


if __name__ == "__main__":
    main()
