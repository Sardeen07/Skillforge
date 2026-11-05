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

import random, re


@check("url-safe-and-long")
def _():
    r = load("reset")
    tok = r.new_reset_token()
    assert re.fullmatch(r"[A-Za-z0-9_\-]+", tok), tok
    assert len(tok) >= 22, f"{len(tok)} characters is under 128 bits"


@check("unique")
def _():
    r = load("reset")
    toks = {r.new_reset_token() for _ in range(2000)}
    assert len(toks) == 2000


@check("not-from-seedable-prng")
def _():
    r = load("reset")
    random.seed(12345); a = r.new_reset_token()
    random.seed(12345); b = r.new_reset_token()
    assert a != b, "token is reproducible from the random module's seed"


if __name__ == "__main__":
    main()
