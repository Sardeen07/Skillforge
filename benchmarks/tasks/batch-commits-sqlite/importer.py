import sqlite3


def open_db(path):
    conn = sqlite3.connect(path)
    conn.execute("create table if not exists events (id integer primary key, kind text not null, payload text)")
    conn.commit()
    return conn


def import_events(conn, rows):
    """Insert (kind, payload) rows."""
    for kind, payload in rows:
        conn.execute("insert into events (kind, payload) values (?, ?)", (kind, payload))
        conn.commit()
