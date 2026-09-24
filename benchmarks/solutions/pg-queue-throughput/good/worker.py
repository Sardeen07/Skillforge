"""Order fulfilment worker.

Eight of these run concurrently in production, all against the same jobs table.

A separate reaper (see ops/reaper.md) already requeues any job left in 'processing'
for more than ten minutes, so a worker dying mid-job is recovered without holding
anything open.
"""
from billing import charge_card


def claim_next_job(conn):
    """Take the oldest pending job, charge the customer, and mark the job done."""
    # Claim in a short transaction: skip rows other workers hold, mark ours, release.
    conn.execute("begin")
    row = conn.execute(
        """
        select id, order_id, amount
        from jobs
        where status = 'pending'
        order by created_at
        limit 1
        for update skip locked
        """
    ).fetchone()
    if row is None:
        conn.execute("commit")
        return None
    job_id, order_id, amount = row
    conn.execute(
        "update jobs set status = 'processing', started_at = now() where id = %s",
        (job_id,),
    )
    conn.execute("commit")

    # The slow payment call runs with no lock held; the reaper requeues on a crash.
    receipt = charge_card(order_id, amount)

    conn.execute("begin")
    conn.execute(
        "update jobs set status = 'done', receipt = %s where id = %s",
        (receipt, job_id),
    )
    conn.execute("commit")
    return job_id


def orders_page(conn, page, per_page=50):
    """One page of the orders report, newest first. Kept for existing callers."""
    return conn.execute(
        """
        select id, customer_id, total, created_at
        from orders
        order by created_at desc, id desc
        limit %s offset %s
        """,
        (per_page, page * per_page),
    ).fetchall()


def orders_page_after(conn, cursor=None, per_page=50):
    """The next page of the orders report after `cursor` = (created_at, id) of the last row seen."""
    if cursor is None:
        return conn.execute(
            """
            select id, customer_id, total, created_at
            from orders
            order by created_at desc, id desc
            limit %s
            """,
            (per_page,),
        ).fetchall()
    return conn.execute(
        """
        select id, customer_id, total, created_at
        from orders
        where (created_at, id) < (%s, %s)
        order by created_at desc, id desc
        limit %s
        """,
        (cursor[0], cursor[1], per_page),
    ).fetchall()


def customer_orders(conn, customer_id):
    """Every order belonging to one customer, for the account page."""
    return conn.execute(
        "select id, total, created_at from orders where customer_id = %s",
        (customer_id,),
    ).fetchall()
