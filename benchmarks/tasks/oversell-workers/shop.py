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
        (stock,) = conn.execute("select stock from items where sku = ?", (sku,)).fetchone()
        if stock < qty:
            return False
        time.sleep(0.01)  # payment authorization
        conn.execute("update items set stock = ? where sku = ?", (stock - qty, sku))
        conn.commit()
        return True
    finally:
        conn.close()
