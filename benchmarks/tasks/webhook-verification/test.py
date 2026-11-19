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

import hashlib, hmac, json


def _signed(body, t, secret=b"whsec_test_7f3a"):
    sig = hmac.new(secret, f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return {"Provider-Signature": f"t={t},v1={sig}"}


BODY = json.dumps({"id": "evt_1", "type": "charge.succeeded", "amount": 500}).encode()


def _rejects(w, headers, body, now):
    try:
        w.verify_webhook(headers, body, now=now)
    except w.InvalidSignature:
        return True
    return False


@check("accepts-genuine-event")
def _():
    w = load("webhooks"); now = 1_800_000_000
    assert w.verify_webhook(_signed(BODY, now), BODY, now=now + 5)["id"] == "evt_1"


@check("rejects-tampering-and-wrong-secret")
def _():
    w = load("webhooks"); now = 1_800_000_000
    tampered = BODY.replace(b"500", b"50000")
    assert _rejects(w, _signed(BODY, now), tampered, now), "accepted a modified body"
    assert _rejects(w, _signed(BODY, now, b"other-secret"), BODY, now), "accepted a signature from another secret"
    assert _rejects(w, {}, BODY, now), "accepted a request with no signature header"


@check("rejects-replayed-old-events")
def _():
    w = load("webhooks"); now = 1_800_000_000
    captured = _signed(BODY, now - 3600)
    assert _rejects(w, captured, BODY, now), "a genuine request captured an hour ago was accepted again"


if __name__ == "__main__":
    main()
