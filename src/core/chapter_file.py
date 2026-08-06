def render_chapter(title: str, body: str) -> str:
    """Render a chapter markdown file: a title heading then its body."""
    return f"# {title}\n\n{body}\n"


def read_body(text: str) -> str:
    """Return chapter body text, dropping a leading title heading."""
    lines = text.split("\n")
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()
