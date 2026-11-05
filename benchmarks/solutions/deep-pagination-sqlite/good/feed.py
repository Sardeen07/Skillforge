import base64
import json
import sqlite3


def setup(n=200_000):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table events (id integer primary key, created_at integer not null, body text)")
    conn.executemany("insert into events (created_at, body) values (?, ?)",
                     ((i // 3, f"event {i}") for i in range(n)))
    conn.execute("create index events_created on events (created_at)")
    conn.execute("create index if not exists events_created_id on events (created_at, id)")
    return conn


def list_events(conn, page, per_page=50):
    """Newest first. page starts at 1. Deep pages are slow; use list_events_after."""
    return conn.execute("select id, created_at, body from events order by created_at desc, id desc "
                        "limit ? offset ?", (per_page, (page - 1) * per_page)).fetchall()


def _encode(row):
    return base64.urlsafe_b64encode(json.dumps([row[1], row[0]]).encode()).decode()


def list_events_after(conn, before=None, per_page=50):
    """(events newest first, cursor for the next page or None). Keyset pagination: a page
    costs the same however deep it is, and new events never shift later pages."""
    if before is None:
        rows = conn.execute("select id, created_at, body from events order by created_at desc, id desc limit ?",
                            (per_page,)).fetchall()
    else:
        created, last_id = json.loads(base64.urlsafe_b64decode(before))
        rows = conn.execute("select id, created_at, body from events where (created_at, id) < (?, ?) "
                            "order by created_at desc, id desc limit ?", (created, last_id, per_page)).fetchall()
    return rows, (_encode(rows[-1]) if len(rows) == per_page else None)
