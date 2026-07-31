# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

from .canonical import deep_json_copy
from .exceptions import ContentSchemaUnsupported

CURRENT_CONTENT_SCHEMA_VERSION = 2
SCHEMA_DIRECTORY = Path(__file__).resolve().parents[4] / "schemas" / "content"


@lru_cache(maxsize=1)
def schema_registry() -> dict[int, dict[str, Any]]:
    registry: dict[int, dict[str, Any]] = {}
    for version in (1, 2):
        path = SCHEMA_DIRECTORY / f"unit-document-v{version}.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        for item in _walk_schema(schema):
            reference = item.get("$ref")
            if isinstance(reference, str) and not reference.startswith("#/"):
                raise RuntimeError(
                    "El schema de contenido no puede usar referencias remotas."
                )
        registry[version] = schema
    return registry


def _walk_schema(value: object):
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            yield current
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


@lru_cache(maxsize=4)
def validator_for(schema_version: int) -> Draft202012Validator:
    schema = schema_registry().get(schema_version)
    if schema is None:
        raise ContentSchemaUnsupported(
            "La versión del schema de contenido no está soportada.",
            path="schema_version",
        )
    return Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
        registry=Registry(retrieve=lambda uri: _reject_remote_reference(uri)),
    )


def _reject_remote_reference(uri: str):
    raise ContentSchemaUnsupported(
        "El documento intentó resolver un schema externo.", path="content"
    )


def migrate_document(
    content: object, *, from_version: int, to_version: int
) -> dict[str, Any]:
    if from_version == to_version and from_version in schema_registry():
        copied = deep_json_copy(content)
    elif from_version == 1 and to_version == 2:
        copied = deep_json_copy(content)
    else:
        raise ContentSchemaUnsupported(
            "No existe una migración explícita para esa versión del documento.",
            path="schema_version",
        )
    if not isinstance(copied, dict):
        raise ContentSchemaUnsupported("El documento no tiene una raíz válida.")
    return copied


def empty_document(node_id: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "attrs": {"nodeId": node_id}}],
    }
