# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

_WORD = re.compile(r"\b[\wÀ-ÖØ-öø-ÿ]+\b", re.UNICODE)
_BREAK_AFTER = {
    "paragraph",
    "heading",
    "blockquote",
    "listItem",
    "pedagogicalBlock",
    "displayMath",
    "codeBlock",
    "tableRow",
}


@dataclass(frozen=True)
class ContentMetrics:
    plain_text: str
    character_count: int
    word_count: int
    node_count: int


def iter_nodes(content: object) -> Iterator[tuple[dict[str, Any], str]]:
    pending: list[tuple[object, str]] = [(content, "content")]
    while pending:
        current, path = pending.pop()
        if not isinstance(current, dict):
            continue
        yield current, path
        children = current.get("content")
        if isinstance(children, list):
            for index in range(len(children) - 1, -1, -1):
                pending.append((children[index], f"{path}.content.{index}"))


def extract_metrics(content: object) -> ContentMetrics:
    pieces: list[str] = []
    node_count = 0
    pending: list[tuple[object, bool]] = [(content, False)]
    while pending:
        current, closing = pending.pop()
        if not isinstance(current, dict):
            continue
        node_type = current.get("type")
        if closing:
            if node_type in _BREAK_AFTER and pieces and pieces[-1] != "\n":
                pieces.append("\n")
            continue
        node_count += 1
        attrs = current.get("attrs")
        if isinstance(attrs, dict):
            for key in ("title", "latex", "caption", "code"):
                value = attrs.get(key)
                if isinstance(value, str) and value:
                    pieces.append(value)
                    pieces.append("\n" if key in {"code", "caption"} else " ")
        if node_type == "text":
            text = current.get("text")
            if isinstance(text, str):
                pieces.append(text)
        elif node_type == "hardBreak":
            pieces.append("\n")
        pending.append((current, True))
        children = current.get("content")
        if isinstance(children, list):
            for child in reversed(children):
                pending.append((child, False))
    plain_text = re.sub(r"[ \t]+\n", "\n", "".join(pieces))
    plain_text = re.sub(r"\n{3,}", "\n\n", plain_text).strip()
    return ContentMetrics(
        plain_text=plain_text,
        character_count=len(plain_text),
        word_count=len(_WORD.findall(plain_text)),
        node_count=node_count,
    )


def has_meaningful_content(content: object) -> bool:
    for node, _path in iter_nodes(content):
        node_type = node.get("type")
        if node_type == "text" and str(node.get("text", "")).strip():
            return True
        attrs = node.get("attrs")
        if not isinstance(attrs, dict):
            continue
        if (
            node_type in {"inlineMath", "displayMath"}
            and str(attrs.get("latex", "")).strip()
        ):
            return True
        if node_type == "codeBlock" and str(attrs.get("code", "")).strip():
            return True
    return False
