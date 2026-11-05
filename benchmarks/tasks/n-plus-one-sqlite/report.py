import sqlite3


def setup(n_customers=50, orders_each=3):
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        create table customers (id integer primary key, name text);
        create table orders (id integer primary key, customer_id integer references customers(id), amount_cents integer);
    """)
    for c in range(1, n_customers + 1):
        conn.execute("insert into customers values (?, ?)", (c, f"Customer {c:04d}"))
        for k in range(orders_each):
            conn.execute("insert into orders (customer_id, amount_cents) values (?, ?)", (c, 100 * c + k))
    conn.execute("insert into customers values (?, ?)", (n_customers + 1, "No Orders Ltd"))
    return conn


def customer_totals(conn):
    """[(name, total_cents)] for every customer, sorted by name; customers without orders total 0."""
    out = []
    for cid, name in conn.execute("select id, name from customers order by name").fetchall():
        total = conn.execute("select coalesce(sum(amount_cents), 0) from orders where customer_id = ?",
                             (cid,)).fetchone()[0]
        out.append((name, total))
    return out
