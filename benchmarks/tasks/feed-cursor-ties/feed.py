import sqlite3


def setup(n=500, per_second=12):
    """Posts arrive in bursts: many share the same created_at second (bulk imports)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("create table posts (id integer primary key, created_at integer not null, body text)")
    conn.executemany("insert into posts (created_at, body) values (?, ?)",
                     ((i // per_second, f"post {i}") for i in range(n)))
    return conn


def page(conn, page_no, limit=20):
    """Newest first; page_no starts at 1."""
    return conn.execute("select id, created_at, body from posts order by created_at desc limit ? offset ?",
                        (limit, (page_no - 1) * limit)).fetchall()
