import sqlite3
import time


def connect(path):
    return sqlite3.connect(path, timeout=30)


def setup(path, stock):
    conn = connect(path)
    conn.execute("create table if not exists items (sku text primary key, stock integer not null)")
    conn.execute("delete from items")
    conn.execute("insert into items values ('mug', ?)", (stock,))
    conn.commit()
    conn.close()


def buy(path, sku, qty=1):
    """Reserve qty units of sku. Returns True if reserved, False if out of stock."""
    conn = connect(path)
    try:
        time.sleep(0.01)  # payment authorization
        # One atomic statement: the check and the decrement cannot interleave with another
        # worker *process* (gunicorn runs several), which an in-process lock cannot prevent.
        cur = conn.execute("update items set stock = stock - ? where sku = ? and stock >= ?", (qty, sku, qty))
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()
