from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SnippetSegment:
    text: str
    highlighted: bool


def safe_snippet(text: str, query: str, *, limit: int = 280) -> list[SnippetSegment]:
    clean = " ".join(text.split())[:200_000]
    terms = sorted(
        {item for item in query.split() if len(item) >= 2}, key=len, reverse=True
    )
    if not terms:
        return [SnippetSegment(clean[:limit], False)]
    matcher = re.compile(
        "(" + "|".join(re.escape(term) for term in terms) + ")", re.IGNORECASE
    )
    first = matcher.search(clean)
    start = max(0, (first.start() if first else 0) - limit // 3)
    excerpt = clean[start : start + limit]
    segments: list[SnippetSegment] = []
    cursor = 0
    for match in matcher.finditer(excerpt):
        if match.start() > cursor:
            segments.append(SnippetSegment(excerpt[cursor : match.start()], False))
        segments.append(SnippetSegment(match.group(0), True))
        cursor = match.end()
    if cursor < len(excerpt):
        segments.append(SnippetSegment(excerpt[cursor:], False))
    return segments or [SnippetSegment(excerpt, False)]
