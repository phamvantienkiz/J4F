import re


_PIPE_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_PIPE_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_MARKDOWN_HEADER = re.compile(r"(#{2,3})(?!#)\s+")


def _strip_pipe_tables(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    table_buffer: list[str] = []

    def flush_table_buffer() -> None:
        table_buffer.clear()

    for line in lines:
        is_table_line = bool(_PIPE_TABLE_ROW.match(line) or _PIPE_TABLE_SEPARATOR.match(line))
        if is_table_line:
            table_buffer.append(line)
            continue
        flush_table_buffer()
        kept.append(line)

    return "\n".join(kept)


def _ensure_header_spacing(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        start = match.start()
        if start == 0:
            return "\n\n" + match.group(0)
        if text[max(0, start - 2):start] == "\n\n":
            return match.group(0)
        prefix = "\n" if text[start - 1:start] == "\n" else "\n\n"
        return prefix + match.group(0)

    return _MARKDOWN_HEADER.sub(replace, text)


def sanitize_markdown_layout(text: str) -> str:
    if not text:
        return text

    without_tables = _strip_pipe_tables(text)
    spaced_headers = _ensure_header_spacing(without_tables)
    return re.sub(r"\n{3,}", "\n\n", spaced_headers).rstrip()
