"""Order fulfilment worker.

Eight of these run concurrently in production, all against the same jobs table.

A separate reaper (see ops/reaper.md) already requeues any job left in 'processing'
for more than ten minutes, so a worker dying mid-job is recovered without holding
anything open.
"""
from billing import charge_card


def claim_next_job(conn):
    """Take the oldest pending job, charge the customer, and mark the job done."""
    conn.execute("begin")

    row = conn.execute(
        """
        select id, order_id, amount
        from jobs
        where status = 'pending'
        order by created_at
        limit 1
        for update
        """
    ).fetchone()

    if row is None:
        conn.execute("commit")
        return None

    job_id, order_id, amount = row
    conn.execute("update jobs set status = 'processing' where id = %s", (job_id,))

    receipt = charge_card(order_id, amount)

    conn.execute(
        "update jobs set status = 'done', receipt = %s where id = %s",
        (receipt, job_id),
    )
    conn.execute("commit")
    return job_id


def orders_page(conn, page, per_page=50):
    """One page of the orders report, newest first."""
    return conn.execute(
        """
        select id, customer_id, total, created_at
        from orders
        order by created_at desc, id desc
        limit %s offset %s
        """,
        (per_page, page * per_page),
    ).fetchall()


def customer_orders(conn, customer_id):
    """Every order belonging to one customer, for the account page."""
    return conn.execute(
        "select id, total, created_at from orders where customer_id = %s",
        (customer_id,),
    ).fetchall()
