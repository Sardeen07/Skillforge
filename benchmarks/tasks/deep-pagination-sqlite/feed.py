import sqlite3


def setup(n=200_000):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table events (id integer primary key, created_at integer not null, body text)")
    conn.executemany("insert into events (created_at, body) values (?, ?)",
                     ((i // 3, f"event {i}") for i in range(n)))
    conn.execute("create index events_created on events (created_at)")
    return conn


def list_events(conn, page, per_page=50):
    """Newest first. page starts at 1."""
    return conn.execute("select id, created_at, body from events order by created_at desc, id desc "
                        "limit ? offset ?", (per_page, (page - 1) * per_page)).fetchall()
