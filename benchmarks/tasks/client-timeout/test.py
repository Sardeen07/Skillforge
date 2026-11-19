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

import socket, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# The test servers are on 127.0.0.1. Some machines (e.g. CI macOS images) route urllib through a
# system proxy, which cannot reach the grader's loopback servers; this is not what is graded.
os.environ["no_proxy"] = os.environ["NO_PROXY"] = "*"


class OK(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"status": "green"}'
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def _ok_server():
    srv = HTTPServer(("127.0.0.1", 0), OK)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/status"


def _silent_server():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(5)
    held = []
    threading.Thread(target=lambda: [held.append(s.accept()) for _ in range(5)], daemon=True).start()
    return f"http://127.0.0.1:{s.getsockname()[1]}/status", held


@check("works")
def _():
    c = load("client")
    assert c.fetch_status(_ok_server()) == {"status": "green"}


@check("default-timeout", timeout=15)
def _():
    c = load("client")
    url, _ = _silent_server()
    start = time.perf_counter()
    try:
        c.fetch_status(url)
    except TimeoutError:
        took = time.perf_counter() - start
        assert took <= 6, f"gave up after {took:.1f}s"
        return
    raise AssertionError("returned without data or timing out")


@check("custom-timeout", timeout=15)
def _():
    c = load("client")
    url, _ = _silent_server()
    start = time.perf_counter()
    try:
        c.fetch_status(url, timeout=0.5)
    except TimeoutError:
        assert time.perf_counter() - start < 2.5
        return
    raise AssertionError("no TimeoutError")


if __name__ == "__main__":
    main()
