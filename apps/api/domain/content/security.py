from __future__ import annotations

import re
from urllib.parse import urlsplit

from .exceptions import ContentUnsafeLink, ContentUnsafeMath
from .limits import MAX_URL_CHARACTERS

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_MATH = re.compile(
    r"(?:\\(?:require|style|class|cssId|htmlClass|htmlId|htmlStyle|href)\b|"
    r"<\s*/?\s*tex-html\b|javascript\s*:|data\s*:)",
    re.IGNORECASE,
)


def validate_link(href: str, *, path: str) -> None:
    if (
        not href
        or len(href) > MAX_URL_CHARACTERS
        or _CONTROL_CHARACTERS.search(href)
        or "\\" in href
        or href.startswith("//")
    ):
        raise ContentUnsafeLink("El enlace no es seguro.", path=path)
    if href.startswith("#"):
        if len(href) == 1 or any(character.isspace() for character in href):
            raise ContentUnsafeLink("El fragmento del enlace no es válido.", path=path)
        return
    if href.startswith("/"):
        return
    parsed = urlsplit(href)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ContentUnsafeLink(
            "Sólo se permiten enlaces HTTP(S), rutas internas y fragmentos.",
            path=path,
        )


def validate_math(latex: str, *, path: str) -> None:
    if _CONTROL_CHARACTERS.search(latex) or _UNSAFE_MATH.search(latex):
        raise ContentUnsafeMath(
            "La fórmula contiene una capacidad no permitida.", path=path
        )
