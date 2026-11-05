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

import base64, json


def _forge(t, claims=None, header=None, sig=None):
    h, p, s = t.split(".")
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return ".".join([enc(header) if header else h, enc(claims) if claims else p, s if sig is None else sig])


@check("accepts-valid")
def _():
    t = load("tokens")
    tok = t.encode_token({"sub": "42", "exp": int(time.time()) + 600})
    assert t.decode_token(tok)["sub"] == "42"


@check("rejects-tampered-payload")
def _():
    t = load("tokens")
    tok = t.encode_token({"sub": "42", "exp": int(time.time()) + 600})
    bad = _forge(tok, claims={"sub": "1", "exp": int(time.time()) + 600})
    try:
        t.decode_token(bad)
    except t.InvalidToken:
        return
    raise AssertionError("tampered token accepted")


@check("rejects-alg-none")
def _():
    t = load("tokens")
    tok = t.encode_token({"sub": "42", "exp": int(time.time()) + 600})
    bad = _forge(tok, header={"alg": "none", "typ": "JWT"}, sig="")
    try:
        t.decode_token(bad)
    except t.InvalidToken:
        return
    raise AssertionError("alg none token accepted")


@check("rejects-expired")
def _():
    t = load("tokens")
    tok = t.encode_token({"sub": "42", "exp": int(time.time()) - 5})
    try:
        t.decode_token(tok)
    except t.InvalidToken:
        return
    raise AssertionError("expired token accepted")


if __name__ == "__main__":
    main()
