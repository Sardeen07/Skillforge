import time


def build_pdf(order_id):
    """A slow, synchronous third-party call we cannot change."""
    time.sleep(0.6)
    return f"%PDF-{order_id}"


async def render_report(order_id):
    pdf = build_pdf(order_id)
    return {"order_id": order_id, "bytes": len(pdf), "pdf": pdf}


async def health():
    return "ok"
