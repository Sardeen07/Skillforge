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


def page_after(conn, cursor=None, limit=20):
    """(posts newest first, cursor for the next page or None). The cursor is the last row's
    (created_at, id): created_at alone is not unique, so it would skip or repeat posts."""
    if cursor is None:
        rows = conn.execute("select id, created_at, body from posts order by created_at desc, id desc limit ?",
                            (limit,)).fetchall()
    else:
        created_at, last_id = (int(x) for x in cursor.split(":"))
        rows = conn.execute("select id, created_at, body from posts where (created_at, id) < (?, ?) "
                            "order by created_at desc, id desc limit ?", (created_at, last_id, limit)).fetchall()
    return rows, (f"{rows[-1][1]}:{rows[-1][0]}" if len(rows) == limit else None)
