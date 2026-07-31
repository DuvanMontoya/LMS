# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportGeneralTypeIssues=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema.exceptions import ValidationError

from .canonical import canonical_json_bytes, content_digest, deep_json_copy
from .exceptions import (
    ContentDuplicateNodeId,
    ContentInvalidCodeLanguage,
    ContentNodeLimitExceeded,
    ContentSchemaInvalid,
    ContentTooDeep,
    ContentTooLarge,
)
from .extraction import ContentMetrics, extract_metrics, iter_nodes
from .limits import (
    MAX_DEPTH,
    MAX_NODES,
    MAX_SERIALIZED_BYTES,
    MAX_TEXT_CHARACTERS,
    MAX_TOP_LEVEL_BLOCKS,
)
from .schemas import validator_for
from .security import validate_link, validate_math

ALLOWED_CODE_LANGUAGES = frozenset(
    {"plaintext", "python", "javascript", "typescript", "json", "sql", "latex"}
)
ASSET_NODE_TYPES = frozenset(
    {"imageAsset", "audioAsset", "videoAsset", "documentAsset", "datasetAsset"}
)


@dataclass(frozen=True)
class ValidatedContent:
    content: dict[str, Any]
    metrics: ContentMetrics
    digest: str


def _safe_path(parts: object) -> str:
    if not parts:
        return "content"
    return "content." + ".".join(str(item) for item in parts)


def _prescan(content: object) -> None:
    try:
        serialized = canonical_json_bytes(content)
    except (TypeError, ValueError, OverflowError) as error:
        raise ContentSchemaInvalid(
            "El documento debe contener únicamente valores JSON válidos."
        ) from error
    if len(serialized) > MAX_SERIALIZED_BYTES:
        raise ContentTooLarge("El documento supera el límite de 1 MiB.")

    nodes = 0
    text_characters = 0
    pending: list[tuple[object, int, str]] = [(content, 1, "content")]
    while pending:
        current, depth, path = pending.pop()
        if depth > MAX_DEPTH:
            raise ContentTooDeep(
                "El documento supera la profundidad máxima.", path=path
            )
        if isinstance(current, dict):
            if "type" in current:
                nodes += 1
                if nodes > MAX_NODES:
                    raise ContentNodeLimitExceeded(
                        "El documento supera el máximo de nodos.", path=path
                    )
            for key, value in current.items():
                if not isinstance(key, str):
                    raise ContentSchemaInvalid(
                        "Las claves JSON deben ser texto.", path=path
                    )
                pending.append((value, depth + 1, f"{path}.{key}"))
        elif isinstance(current, list):
            if path == "content.content" and len(current) > MAX_TOP_LEVEL_BLOCKS:
                raise ContentNodeLimitExceeded(
                    "El documento supera el máximo de bloques.", path=path
                )
            for index, value in enumerate(current):
                pending.append((value, depth + 1, f"{path}.{index}"))
        elif isinstance(current, str):
            text_characters += len(current)
            if text_characters > MAX_TEXT_CHARACTERS:
                raise ContentTooLarge(
                    "El documento supera el máximo de caracteres.", path=path
                )
        elif current is not None and not isinstance(current, (bool, int, float)):
            raise ContentSchemaInvalid(
                "El documento contiene un valor que no pertenece a JSON.", path=path
            )


def _validate_schema(content: object, schema_version: int) -> None:
    errors = sorted(
        validator_for(schema_version).iter_errors(content),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        error: ValidationError = errors[0]
        raise ContentSchemaInvalid(
            "El documento no cumple el contrato semántico.",
            path=_safe_path(error.absolute_path),
        )
    if schema_version == 2:
        _validate_legacy_nodes_with_v1(content)


def _validate_legacy_nodes_with_v1(content: object) -> None:
    copied = deep_json_copy(content)
    if not isinstance(copied, dict) or not isinstance(copied.get("content"), list):
        return

    def replace_assets(value: object, *, asset_allowed: bool = False) -> object:
        if isinstance(value, list):
            return [replace_assets(item) for item in value]
        if not isinstance(value, dict):
            return value
        node_type = value.get("type")
        if node_type in ASSET_NODE_TYPES:
            if not asset_allowed:
                raise ContentSchemaInvalid(
                    "Los recursos académicos deben ser bloques de primer nivel.",
                    path="content",
                )
            attrs = value.get("attrs")
            node_id = attrs.get("nodeId") if isinstance(attrs, dict) else None
            return {"type": "paragraph", "attrs": {"nodeId": node_id}}
        return {key: replace_assets(item) for key, item in value.items()}

    transformed = {
        **copied,
        "content": [
            replace_assets(item, asset_allowed=True) for item in copied["content"]
        ],
    }
    errors = sorted(
        validator_for(1).iter_errors(transformed),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        raise ContentSchemaInvalid(
            "Los nodos heredados no cumplen el contrato v1.",
            path=_safe_path(errors[0].absolute_path),
        )


def _validate_semantics(content: dict[str, Any]) -> None:
    node_ids: set[str] = set()
    for node, path in iter_nodes(content):
        attrs = node.get("attrs")
        if isinstance(attrs, dict):
            node_id = attrs.get("nodeId")
            if isinstance(node_id, str):
                if node_id in node_ids:
                    raise ContentDuplicateNodeId(
                        "Cada nodo debe tener un identificador único.",
                        path=f"{path}.attrs.nodeId",
                    )
                node_ids.add(node_id)
        if node.get("type") in {"inlineMath", "displayMath"} and isinstance(
            attrs, dict
        ):
            validate_math(str(attrs.get("latex", "")), path=f"{path}.attrs.latex")
        if node.get("type") == "codeBlock" and isinstance(attrs, dict):
            language = attrs.get("language")
            if language not in ALLOWED_CODE_LANGUAGES:
                raise ContentInvalidCodeLanguage(
                    "El lenguaje del bloque de código no está permitido.",
                    path=f"{path}.attrs.language",
                )
        if node.get("type") == "text":
            marks = node.get("marks", [])
            if isinstance(marks, list):
                seen_marks: set[str] = set()
                for index, mark in enumerate(marks):
                    if not isinstance(mark, dict):
                        continue
                    mark_type = str(mark.get("type", ""))
                    if mark_type in seen_marks:
                        raise ContentSchemaInvalid(
                            "Una marca no puede repetirse en el mismo texto.",
                            path=f"{path}.marks.{index}",
                        )
                    seen_marks.add(mark_type)
                    if mark_type == "link":
                        mark_attrs = mark.get("attrs")
                        if isinstance(mark_attrs, dict):
                            validate_link(
                                str(mark_attrs.get("href", "")),
                                path=f"{path}.marks.{index}.attrs.href",
                            )
        if node.get("type") == "table":
            rows = node.get("content")
            if isinstance(rows, list) and rows:
                for row_index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        continue
                    cells = row.get("content")
                    expected_type = "tableHeader" if row_index == 0 else "tableCell"
                    if not isinstance(cells, list) or any(
                        not isinstance(cell, dict) or cell.get("type") != expected_type
                        for cell in cells
                    ):
                        raise ContentSchemaInvalid(
                            "La primera fila debe usar encabezados y las demás celdas de datos.",
                            path=f"{path}.content.{row_index}",
                        )
                widths = [
                    len(row.get("content", [])) for row in rows if isinstance(row, dict)
                ]
                if not widths or len(set(widths)) != 1:
                    raise ContentSchemaInvalid(
                        "Todas las filas de la tabla deben tener el mismo número de columnas.",
                        path=f"{path}.content",
                    )


def validate_content(content: object, *, schema_version: int) -> ValidatedContent:
    _prescan(content)
    _validate_schema(content, schema_version)
    copied = deep_json_copy(content)
    if not isinstance(copied, dict):
        raise ContentSchemaInvalid("La raíz del documento debe ser un objeto.")
    _validate_semantics(copied)
    metrics = extract_metrics(copied)
    return ValidatedContent(
        content=copied, metrics=metrics, digest=content_digest(copied)
    )


def validate_schema_contract() -> None:
    validator_for.cache_clear()
    validator_for(1)
    validator_for(2)
