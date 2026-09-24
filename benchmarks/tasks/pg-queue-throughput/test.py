"""Hidden test for the pg-queue-throughput task. Never shown to the agent.

Four defects, chosen because the obvious fix is not the correct one:

  skip-locked        `for update` is already there, so "add a lock" changes nothing;
                     the workers need `for update skip locked` to stop queueing up
  short-transaction  a 2-5s payment call sits inside the claim transaction, holding
                     a row lock for its whole duration
  keyset-pagination  `offset` re-scans every skipped row, so deep pages degrade;
                     passes when a keyset path exists, since task.txt asks for the
                     old behaviour to be kept
  fk-index           Postgres does not index foreign keys automatically, so
                     orders.customer_id has no index and the account page scans

Grader v2. With a Postgres available (pgserver + psycopg, see requirements-dev.txt),
skip-locked, short-transaction and fk-index are checked by behavior against a real,
throwaway database: concurrent workers must claim distinct jobs and skip a job another
worker holds; no row lock may be held while the payment call runs; the migrations must
create an index led by orders.customer_id. keyset-pagination stays a static check,
because the agent may name its cursor function anything. Static checks read only SQL
string literals with comments removed, so a fix written only in a comment never counts
(v1 was fooled by exactly that). Without Postgres every check is static; the output
says which mode ran. Prints SCORE: n/4 and exits 0 only when all four hold.
"""
import ast
import importlib.util
import os
import re
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

GRADER_VERSION = 2
HERE = Path(__file__).parent
WORKER = HERE / "worker.py"


# ---------------------------------------------------------------- static helpers
def sql_literals(tree):
    """Every string literal in the worker, lowercased, with SQL comments removed."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = re.sub(r"--[^\n]*", " ", node.value)
            text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
            out.append(" ".join(text.lower().split()))
    return out


def strip_sql_comments(sql):
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)


def _executes(node):
    """The literal SQL of a `<conn>.execute("...")` call, lowercased, else None."""
    if not isinstance(node, ast.Call):
        return None
    fn = node.func
    if not (isinstance(fn, ast.Attribute) and fn.attr in ("execute", "executemany")):
        return None
    if not node.args:
        return None
    arg = node.args[0]
    return arg.value.strip().lower() if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None


def _calls_charge(node):
    return any(isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == "charge_card"
               for n in ast.walk(node))


def _opens_transaction(stmt):
    if not isinstance(stmt, (ast.With, ast.AsyncWith)):
        return False
    for item in stmt.items:
        ctx = item.context_expr
        if isinstance(ctx, ast.Call) and getattr(ctx.func, "attr", None) == "transaction":
            return True
        if getattr(ctx, "attr", None) == "transaction":
            return True
    return False


def static_skip_locked(tree, _sql):
    literals = sql_literals(tree)
    if any(re.search(r"for update skip locked", s) for s in literals):
        return True, "claims use `for update skip locked` (static)"
    if any(re.search(r"for update", s) for s in literals):
        return False, "still plain `for update`, so workers queue behind each other (static)"
    return False, "no row-level locking on the claim at all (static)"


def static_short_transaction(tree, _sql):
    """Walked over each function's top-level statements: the original commits early
    inside an `if row is None:` branch, which a positional regex would call a pass."""
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        open_tx = False
        for stmt in fn.body:
            if _opens_transaction(stmt) and _calls_charge(stmt):
                return False, "payment call is inside a `with conn.transaction():` block (static)"
            if open_tx and _calls_charge(stmt):
                return False, "payment call still runs with the claim transaction open (static)"
            if not isinstance(stmt, (ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            for node in ast.walk(stmt):
                sql = _executes(node)
                if sql is None:
                    continue
                if sql.startswith(("begin", "start transaction")):
                    open_tx = True
                elif sql.startswith(("commit", "rollback", "end")):
                    open_tx = False
    return True, "payment call runs outside the transaction (static)"


def check_keyset_pagination(tree, _sql, _db=None):
    """OFFSET scans and discards every skipped row, so deep pages get slower. Passes when
    a keyset path exists; keeping the old offset function for callers is allowed."""
    literals = sql_literals(tree)
    cursor = any(re.search(r"\(\s*created_at\s*,\s*id\s*\)\s*<", s) or
                 re.search(r"\bwhere\b[^)]*\b(created_at|id)\s*<", s) for s in literals)
    if cursor:
        return True, "a keyset cursor path exists for the orders report (static)"
    if any(re.search(r"\boffset\b", s) for s in literals):
        return False, "orders report still pages only with `offset` (static)"
    return False, "no keyset cursor comparison for the orders report (static)"


def static_fk_index(_tree, sql):
    if re.search(r"create\s+(unique\s+)?index[^;]*\bon\b[^;]*\borders\b[^;]*\(\s*customer_id",
                 strip_sql_comments(sql), re.I | re.S):
        return True, "orders.customer_id is indexed (static)"
    return False, "orders.customer_id is still an unindexed foreign key (static)"


# ---------------------------------------------------------------- behavioral harness
class Database:
    """A throwaway Postgres with the task's migrations applied, or None if unavailable."""

    @classmethod
    def start(cls):
        try:
            import pgserver, psycopg  # noqa: F401
        except ImportError:
            return None
        db = cls()
        db.psycopg = psycopg
        db.dir = tempfile.mkdtemp(prefix="pgq-grade-")
        db.server = pgserver.get_server(db.dir, cleanup_mode="stop")
        db.uri = db.server.get_uri()
        return db

    def connect(self):
        conn = self.psycopg.connect(self.uri, autocommit=True)
        conn.execute("set lock_timeout = '3s'")
        conn.execute("set statement_timeout = '10s'")
        return conn

    def reset(self, sql, jobs=8):
        """Fresh schema from the task's migration files (a list of scripts), then customers,
        orders and pending jobs."""
        with self.connect() as c:
            c.execute("drop schema public cascade")
            c.execute("create schema public")
            for script in sql:
                try:
                    c.execute(script)  # a whole migration file, as a migration tool would run it
                except self.psycopg.errors.ActiveSqlTransaction:
                    # e.g. CREATE INDEX CONCURRENTLY, which cannot run in a multi-statement batch
                    for stmt in [s.strip() for s in strip_sql_comments(script).split(";") if s.strip()]:
                        c.execute(stmt)
            c.execute("insert into customers (email) select 'c' || g || '@x' from generate_series(1, 5) g")
            c.execute("""insert into orders (customer_id, total, created_at)
                         select 1 + g % 5, 10, now() - (g || ' minutes')::interval
                         from generate_series(1, 50) g""")
            c.execute(f"""insert into jobs (order_id, amount, created_at)
                          select g, 10, now() - ((100 - g) || ' seconds')::interval
                          from generate_series(1, {jobs}) g""")

    def stop(self):
        try:
            self.server.cleanup()
        except Exception:
            pass


def load_worker(charge):
    """Import the agent's worker.py with the payment gateway replaced by `charge`."""
    billing = types.ModuleType("billing")
    billing.charge_card = charge
    sys.modules["billing"] = billing
    spec = importlib.util.spec_from_file_location("graded_worker", WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_worker(worker, conn, results, errors):
    try:
        while True:
            job = worker.claim_next_job(conn)
            if job is None:
                return
            results.append(job)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {str(exc).strip().splitlines()[0] if str(exc).strip() else ''}")


def behavioral_skip_locked(db, sql):
    """Concurrent workers claim distinct jobs, and a job another worker holds is skipped."""
    charged, lock = [], threading.Lock()

    def charge(order_id, amount):
        time.sleep(0.2)
        with lock:
            charged.append(order_id)
        return f"r{order_id}"

    worker = load_worker(charge)
    db.reset(sql)
    conns = [db.connect() for _ in range(4)]
    results, errors = [], []
    threads = [threading.Thread(target=run_worker, args=(worker, c, results, errors)) for c in conns]
    for t in threads: t.start()
    for t in threads: t.join(60)
    for c in conns: c.close()
    with db.connect() as c:
        done = c.execute("select count(*) from jobs where status = 'done'").fetchone()[0]
    if errors:
        return False, f"concurrent workers failed: {errors[0]}"
    if sorted(charged) != list(range(1, 9)) or done != 8:
        return False, f"concurrent workers did not each take distinct jobs (charges {sorted(charged)}, done {done}/8)"

    # Another worker holds the oldest job. A correct claim skips it at once.
    db.reset(sql)
    holder, claimant = db.connect(), db.connect()
    try:
        holder.execute("begin")
        held = holder.execute("select id from jobs order by created_at limit 1 for update").fetchone()[0]
        charged.clear()
        started = time.monotonic()
        try:
            job = worker.claim_next_job(claimant)
        except Exception as exc:
            return False, f"a job locked by another worker made the claim fail ({type(exc).__name__})"
        waited = time.monotonic() - started
        holder.execute("rollback")
    finally:
        holder.close(); claimant.close()
    if job is None or job == held:
        return False, "the claim did not take the next free job while one was locked"
    if waited > 1.5:
        return False, f"the claim waited {waited:.1f}s behind another worker's lock"
    return True, "concurrent workers take distinct jobs and skip a locked one"


def behavioral_short_transaction(db, sql):
    """No row lock on the job may be held while the payment call is in flight."""
    probe = db.connect()
    held = []

    def charge(order_id, amount):
        try:
            probe.execute("select id from jobs where order_id = %s for update nowait", (order_id,))
        except db.psycopg.errors.LockNotAvailable:
            held.append(order_id)
        return f"r{order_id}"

    worker = load_worker(charge)
    db.reset(sql, jobs=2)
    conn = db.connect()
    try:
        worker.claim_next_job(conn)
    except Exception as exc:
        return False, f"claim_next_job failed: {type(exc).__name__}"
    finally:
        conn.close(); probe.close()
    if held:
        return False, "the job's row lock is still held while the payment call runs"
    return True, "no row lock is held during the payment call"


def behavioral_fk_index(db, sql):
    db.reset(sql, jobs=0)
    with db.connect() as c:
        rows = c.execute("""
            select i.relname from pg_index x
            join pg_class t on t.oid = x.indrelid join pg_class i on i.oid = x.indexrelid
            join pg_attribute a on a.attrelid = t.oid and a.attnum = x.indkey[0]
            where t.relname = 'orders' and a.attname = 'customer_id'""").fetchall()
    if rows:
        return True, f"orders.customer_id leads index {rows[0][0]}"
    return False, "no index is led by orders.customer_id after the migrations run"


def main():
    if not WORKER.exists():
        print("FAIL  worker.py is missing\nSCORE: 0/4")
        sys.exit(1)
    src = WORKER.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"FAIL  worker.py does not parse: {e}\nSCORE: 0/4")
        sys.exit(1)
    # Any .sql file counts: adding a new migration is the right way to add an index.
    scripts = [p.read_text(encoding="utf-8") for p in sorted(HERE.rglob("*.sql"))]
    sql = "\n".join(scripts)

    # GRADER_MODE=static forces the fallback, so both modes can be validated.
    db = None if os.environ.get("GRADER_MODE") == "static" else Database.start()
    forced = os.environ.get("GRADER_MODE") == "static"
    mode = "behavioral" if db else ("static (forced)" if forced else "static (no Postgres available)")
    print(f"GRADER: v{GRADER_VERSION} {mode}")
    checks = [("skip-locked", behavioral_skip_locked if db else None, static_skip_locked),
              ("short-transaction", behavioral_short_transaction if db else None, static_short_transaction),
              ("keyset-pagination", None, check_keyset_pagination),
              ("fk-index", behavioral_fk_index if db else None, static_fk_index)]
    passed = 0
    try:
        for name, live, static in checks:
            try:
                ok, why = live(db, scripts) if live else static(tree, sql)
            except Exception as exc:  # the agent's code or migrations broke the harness
                ok, why = False, f"could not be checked: {type(exc).__name__}: {str(exc).strip()[:120]}"
            passed += ok
            print(f"{'PASS' if ok else 'FAIL'}  {name:<20} {why}")
    finally:
        if db:
            db.stop()
    print(f"SCORE: {passed}/{len(checks)}")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
