def render_comment(author: str, text: str, website: str) -> str:
    """HTML for one comment. website is the author's homepage link."""
    return (f'<div class="comment"><a href="{website}" title="{author}">{author}</a>'
            f'<p>{text}</p></div>')
