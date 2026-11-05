async def load_dashboard(widget_ids, fetch_widget):
    """[await fetch_widget(id) for each id], in the same order."""
    results = []
    for wid in widget_ids:
        results.append(await fetch_widget(wid))
    return results
