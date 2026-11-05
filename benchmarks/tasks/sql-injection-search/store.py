import sqlite3


def connect():
    conn = sqlite3.connect(":memory:")
    conn.execute("create table products (id integer primary key, name text, published integer)")
    conn.executemany("insert into products (name, published) values (?, ?)", [
        ("Blue Mug", 1), ("Red Mug", 1), ("O'Brien's Tea", 1), ("Secret Prototype", 0)])
    return conn


def search_products(conn, term):
    """Published products whose name contains term (case-insensitive), sorted by name."""
    sql = f"select name from products where published = 1 and name like '%{term}%' order by name"
    return [row[0] for row in conn.execute(sql)]
