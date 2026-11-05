from html import escape
from urllib.parse import urlsplit


def _safe_url(url: str) -> str:
    return url if urlsplit(url.strip()).scheme in ("http", "https") else "#"


def render_comment(author: str, text: str, website: str) -> str:
    """HTML for one comment. website is the author's homepage link."""
    a, t, w = escape(author, quote=True), escape(text, quote=True), escape(_safe_url(website), quote=True)
    return (f'<div class="comment"><a href="{w}" title="{a}">{a}</a>'
            f'<p>{t}</p></div>')
