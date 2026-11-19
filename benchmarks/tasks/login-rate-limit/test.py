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

LB = "10.0.0.2"


def _req(xff):
    return {"REMOTE_ADDR": LB, "HTTP_X_FORWARDED_FOR": xff}


@check("limits-a-client")
def _():
    r = load("ratelimit"); lim = r.LoginLimiter()
    results = [lim.allow(_req("203.0.113.7"), now=1000 + i) for i in range(7)]
    assert results == [True] * 5 + [False] * 2, results


@check("clients-independent-and-window-resets")
def _():
    r = load("ratelimit"); lim = r.LoginLimiter()
    for i in range(5):
        lim.allow(_req("203.0.113.7"), now=1000 + i)
    assert lim.allow(_req("198.51.100.20"), now=1006), "a different client was blocked"
    assert lim.allow(_req("203.0.113.7"), now=1070), "still blocked after the minute passed"


@check("spoofed-header-cannot-bypass")
def _():
    r = load("ratelimit"); lim = r.LoginLimiter()
    # The attacker sends their own X-Forwarded-For; the ALB appends the real address at the end.
    results = [lim.allow(_req(f"1.2.3.{i}, 198.51.100.9"), now=2000 + i) for i in range(8)]
    assert results.count(True) <= 5, f"an attacker rotating a fake X-Forwarded-For got {results.count(True)} attempts in a minute"


if __name__ == "__main__":
    main()
