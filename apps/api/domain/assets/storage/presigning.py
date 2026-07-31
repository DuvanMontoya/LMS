from __future__ import annotations

from urllib.parse import quote


def content_disposition(*, filename: str, inline: bool) -> str:
    disposition = "inline" if inline else "attachment"
    fallback = "".join(
        character
        for character in filename
        if character.isascii() and character.isalnum() or character in "._- "
    ).strip()
    fallback = fallback or "archivo"
    fallback = fallback[:120].replace('"', "")
    encoded = quote(filename, safe="")
    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
