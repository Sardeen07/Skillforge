import sqlite3


def open_db(path):
    conn = sqlite3.connect(path)
    conn.execute("create table if not exists events (id integer primary key, kind text not null, payload text)")
    conn.commit()
    return conn


def import_events(conn, rows):
    """Insert (kind, payload) rows in one transaction: all of them, or none."""
    with conn:
        conn.executemany("insert into events (kind, payload) values (?, ?)", rows)
