from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_query(value: str) -> str:
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value).strip())
    if len(normalized) < 2 or len(normalized) > 200:
        raise ValueError("La búsqueda debe tener entre 2 y 200 caracteres.")
    if len(normalized.split()) > 20:
        raise ValueError("La búsqueda admite máximo 20 términos.")
    if any(unicodedata.category(character) in {"Cc", "Cs"} for character in normalized):
        raise ValueError("La búsqueda contiene caracteres no permitidos.")
    return normalized


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return _WHITESPACE.sub(
        " ",
        "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        ),
    ).strip()
