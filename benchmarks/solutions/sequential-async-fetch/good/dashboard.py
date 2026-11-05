import asyncio


async def load_dashboard(widget_ids, fetch_widget, limit=4):
    """[await fetch_widget(id) for each id], in the same order, at most `limit` at a time."""
    gate = asyncio.Semaphore(limit)

    async def one(wid):
        async with gate:
            return await fetch_widget(wid)

    return await asyncio.gather(*(one(w) for w in widget_ids))
