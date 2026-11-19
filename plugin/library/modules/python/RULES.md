---
module: python
capability: Python correctness, idioms and runtime pitfalls
technologies: python
applies: python, pip, pytest, asyncio, typing, dataclass
checked_against: Python 3.13 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## mutable-default-arguments: Never use a mutable object as a default argument
tags: python, function, default argument, list, dict, shared state, bug
keywords: def, default value, accumulates, persists between calls
refs: https://docs.python.org/3/tutorial/controlflow.html#default-argument-values

Default values are evaluated once, when `def` runs, so a `list`, `dict` or `set` default is shared by every call and keeps whatever earlier calls appended.

```python
def add(item, bucket=None):      # not bucket=[]
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
```

The same applies to dataclass fields: use `field(default_factory=list)`.

## late-binding-closures: Bind loop variables explicitly in closures and lambdas
tags: python, closure, lambda, loop, late binding, callback
keywords: all callbacks use last value
refs: https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result

Closures look up free variables when called, not when created, so callbacks made in a loop all see the loop variable's final value. Bind it at definition time with a default argument or `functools.partial`:

```python
handlers = [lambda i=i: print(i) for i in range(3)]
handlers = [functools.partial(print, i) for i in range(3)]
```

## context-managers-for-resources: Release files, locks and connections with `with`
tags: python, context manager, with statement, file, lock, connection, resource leak
keywords: open, close, finally, contextlib, too many open files
refs: https://docs.python.org/3/reference/compound_stmts.html#the-with-statement

Acquire every resource that must be released (files, sockets, locks, DB connections, temporary directories) in a `with` block so it is released on every path, including exceptions. For your own resources write `__enter__`/`__exit__` or use `contextlib.contextmanager`; for a dynamic number of resources use `contextlib.ExitStack`. Do not rely on garbage collection to close files: on PyPy and under reference cycles it happens late or never.

## specific-exceptions: Catch the narrowest exception and never swallow silently
tags: python, exception, try except, error handling, bare except, logging
keywords: except Exception, pass, traceback, raise from
refs: https://docs.python.org/3/tutorial/errors.html#handling-exceptions

`except:` and `except Exception: pass` hide bugs (and a bare `except:` also catches `KeyboardInterrupt` and `SystemExit`). Catch the specific exception you can handle, keep the `try` body to the line that can raise it, and when translating an error keep the cause: `raise ConfigError("bad port") from exc`. If you must catch broadly at a boundary (a worker loop, a request handler), log with `logger.exception(...)` so the traceback survives.

## asyncio-no-blocking-calls: Never call blocking I/O inside a coroutine
tags: python, asyncio, async, await, blocking, event loop, requests, time sleep
keywords: event loop blocked, run_in_executor, to_thread, latency spikes
refs: https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code

One blocking call (`requests.get`, `time.sleep`, a sync DB driver, heavy CPU work) stalls every task on the event loop. Use async libraries (`httpx.AsyncClient`, `asyncpg`, `asyncio.sleep`), or offload: `await asyncio.to_thread(blocking_fn, arg)`; use a process pool for CPU-bound work. Enable debug mode (`PYTHONASYNCIODEBUG=1`) to log callbacks slower than 100 ms.

## asyncio-keep-task-references: Keep references to tasks and use TaskGroup
tags: python, asyncio, create_task, taskgroup, garbage collection, background task
keywords: task disappeared, never finished, fire and forget, exception never retrieved
refs: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task

The event loop holds only weak references to tasks, so a task created with `asyncio.create_task()` and not stored can be garbage-collected mid-run. Store tasks (for example in a set, removing them with `add_done_callback`), or prefer `async with asyncio.TaskGroup() as tg:` (3.11+), which awaits all children and cancels siblings when one fails.

## asyncio-gather-concurrency: Run independent awaits concurrently, with a bound
tags: python, asyncio, gather, concurrency, semaphore, parallel requests, sequential await
keywords: awaits one after another, rate limit, too many connections
refs: https://docs.python.org/3/library/asyncio-task.html#running-tasks-concurrently

Awaiting independent calls one after another serializes them. Start them together with `asyncio.gather()` or a `TaskGroup`. For large fan-outs, bound concurrency with `asyncio.Semaphore(n)` so you do not exhaust connection pools or hit rate limits; use `return_exceptions=True` only if you then inspect each result.

## dataclasses-for-records: Use dataclasses (or attrs/pydantic) instead of raw dicts and tuples
tags: python, dataclass, record, typing, frozen, slots, model
keywords: dict of fields, namedtuple, typo in key
refs: https://docs.python.org/3/library/dataclasses.html

For structured records, a `@dataclass(frozen=True, slots=True)` gives named fields, a readable `repr`, equality, immutability and lower memory than a dict, and a type checker catches misspelled fields. Use pydantic only where you need validation or parsing of untrusted input at a boundary.

## type-hints-and-checking: Add type hints at module boundaries and run a type checker in CI
tags: python, typing, type hints, mypy, pyright, static analysis, ci
keywords: Optional, None check, Protocol, TypedDict
refs: https://docs.python.org/3/library/typing.html

Annotate public functions, return types and data structures, and run mypy or pyright in CI; hints alone are not checked at runtime. Use `X | None` and narrow before use, `Protocol` for duck-typed interfaces, `TypedDict` for JSON-shaped dicts, and `Sequence`/`Mapping` in parameters (accept broad, return specific).

## iterate-dont-index: Iterate directly; use enumerate, zip and generators
tags: python, loop, enumerate, zip, generator, iterator, memory, idiom
keywords: range(len(, building a list then iterating, large file
refs: https://docs.python.org/3/tutorial/datastructures.html#looping-techniques

Prefer `for item in items`, `enumerate(items)` and `zip(a, b, strict=True)` (3.10+, raises on length mismatch) to index arithmetic. When results are consumed once, use a generator expression instead of building a list, and stream large files line by line (`for line in f`) instead of `f.read()`.

## set-dict-membership: Use sets and dicts for membership and lookups
tags: python, set, dict, membership, lookup, complexity, list, performance
keywords: in list is slow, O(n), nested loop, quadratic
refs: https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset

`x in some_list` is O(n); inside a loop it becomes O(n*m). Build a `set` (or a dict keyed by id) once and test membership in O(1). For counting use `collections.Counter`; for grouping use `defaultdict(list)`.

## string-building: Build large strings with join or io.StringIO
tags: python, string, concatenation, join, performance, loop
keywords: += in loop, quadratic string
refs: https://docs.python.org/3/library/stdtypes.html#str.join

Repeated `s += piece` in a loop can copy the string each time. Collect pieces in a list and `''.join(pieces)` once, or write to `io.StringIO`. Use f-strings for formatting, and lazy `%`-style arguments in logging calls (`logger.info("user %s", uid)`) so unused messages are never formatted.

## subprocess-safely: Run subprocesses with an argument list, a timeout and check=True
tags: python, subprocess, shell injection, security, timeout, command
keywords: os.system, shell=True, user input in command
refs: https://docs.python.org/3/library/subprocess.html#security-considerations

Pass arguments as a list (`subprocess.run(["git", "log", ref], check=True, timeout=30, capture_output=True, text=True)`). Never build a shell string from user input with `shell=True` or `os.system`; if a shell is unavoidable, quote with `shlex.quote`. Always set a timeout and handle `CalledProcessError`/`TimeoutExpired`.

## unsafe-deserialization: Never unpickle or yaml.load untrusted data
tags: python, pickle, yaml, deserialization, security, remote code execution, eval
keywords: pickle.loads, yaml.load, eval, exec, untrusted input
refs: https://docs.python.org/3/library/pickle.html

`pickle.loads`, `marshal`, `shelve` and `yaml.load` with the full loader can execute arbitrary code from crafted input. For untrusted data use JSON, `yaml.safe_load`, or a schema-validated format. Never pass user input to `eval`/`exec`; `ast.literal_eval` parses Python literals only.

## logging-not-print: Use the logging module with per-module loggers
tags: python, logging, print, logger, observability, configuration
keywords: getLogger(__name__), basicConfig in library
refs: https://docs.python.org/3/howto/logging.html

Create `logger = logging.getLogger(__name__)` in each module and configure handlers once, at the application entry point; libraries must not call `basicConfig` or add handlers. Log exceptions with `logger.exception` inside `except`, and never log secrets or full request bodies.

## virtualenv-and-pinning: Isolate environments and pin dependencies
tags: python, venv, pip, dependencies, lock file, reproducible, packaging
keywords: works on my machine, requirements.txt, pyproject, uv, poetry
refs: https://packaging.python.org/en/latest/tutorials/installing-packages/#creating-virtual-environments

Install into a per-project virtual environment (`python -m venv .venv`), never into the system interpreter. Declare dependencies in `pyproject.toml` and commit a lock file (uv, pip-tools or Poetry) so CI and production install the same versions. Run tools as `python -m pip`/`python -m pytest` so they use the interpreter you expect.

## float-money: Use Decimal or integer cents for money, never float
tags: python, float, decimal, money, currency, rounding, precision
keywords: 0.1 + 0.2, rounding error, cents
refs: https://docs.python.org/3/library/decimal.html

Binary floats cannot represent most decimal fractions (`0.1 + 0.2 != 0.3`). Store money as integer minor units or `decimal.Decimal` constructed from strings (`Decimal("19.99")`, not `Decimal(19.99)`), and round explicitly with `quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)` (or the rounding mode your domain requires) at defined points.

## timezone-aware-datetimes: Use timezone-aware datetimes in UTC
tags: python, datetime, timezone, utc, zoneinfo, naive datetime, dst
keywords: utcnow deprecated, off by one hour, daylight saving
refs: https://docs.python.org/3/library/datetime.html#aware-and-naive-objects

Naive datetimes have no zone, so comparisons and arithmetic across zones or DST changes are silently wrong. Create aware values (`datetime.now(timezone.utc)`; `datetime.utcnow()` is deprecated since 3.12 and returns a naive value), store and compute in UTC, and convert with `zoneinfo.ZoneInfo("Europe/Paris")` only for display or for rules like "9am local".

## pytest-fixtures-and-parametrize: Use pytest fixtures and parametrize instead of copy-pasted tests
tags: python, pytest, fixture, parametrize, testing, tmp_path, monkeypatch
keywords: setUp duplication, many similar tests
refs: https://docs.pytest.org/en/stable/how-to/parametrize.html

Express input/expected tables with `@pytest.mark.parametrize`, share setup through fixtures (scoped as narrowly as possible), and use built-ins such as `tmp_path`, `monkeypatch` and `caplog` instead of touching real files, environment or global state. Assert on behavior with plain `assert`; pytest shows the values on failure.

## gil-and-parallelism: Choose threads, processes or async by workload
tags: python, gil, threading, multiprocessing, concurrency, cpu bound, io bound
keywords: threads not faster, ProcessPoolExecutor, free threading
refs: https://docs.python.org/3/library/concurrent.futures.html

In standard CPython the GIL lets only one thread execute Python bytecode at a time: threads help I/O-bound work but not pure-Python CPU work. Use `ProcessPoolExecutor` (or vectorized libraries such as NumPy, which release the GIL) for CPU-bound work, and threads or asyncio for I/O. Free-threaded 3.13 builds are experimental; do not assume them.

## pathlib-and-encoding: Use pathlib and pass encoding explicitly when reading text
tags: python, pathlib, encoding, utf-8, file io, windows, unicode decode error
keywords: UnicodeDecodeError on windows, open without encoding
refs: https://docs.python.org/3/library/pathlib.html

`open(path)` uses the platform's locale encoding, which differs between Linux, macOS and Windows (cp1252), so the same file decodes differently. Pass `encoding="utf-8"` (or enable `PYTHONUTF8=1`), and build paths with `pathlib.Path` rather than string concatenation so separators work everywhere.

## enum-for-closed-sets: Use Enum (or Literal types) for closed sets of values
tags: python, enum, literal, typing, constants, strings, validation
keywords: status == "shiped" typo
refs: https://docs.python.org/3/library/enum.html

Replace magic strings and integers for states and kinds with `enum.Enum`/`StrEnum` (3.11+) or `typing.Literal`, so typos fail at load or type-check time, the set of values is discoverable, and `match` statements can be checked for completeness.
