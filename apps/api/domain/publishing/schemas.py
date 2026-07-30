# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from referencing import Registry, Resource

from .exceptions import ReleaseSnapshotInvalid

CURRENT_RELEASE_SCHEMA_VERSION = 1
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RELEASE_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schemas" / "publication" / "course-release-v1.schema.json"
)
CONTENT_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schemas" / "content" / "unit-document-v1.schema.json"
)
CONTENT_SCHEMA_ID = "urn:lms:content:unit-document:1"


def _walk(value: object):
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            yield current
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


@lru_cache(maxsize=1)
def release_schema() -> dict[str, Any]:
    schema = json.loads(RELEASE_SCHEMA_PATH.read_text(encoding="utf-8"))
    content_schema = json.loads(CONTENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(content_schema)
    allowed_external = {CONTENT_SCHEMA_ID}
    for item in _walk(schema):
        reference = item.get("$ref")
        if (
            isinstance(reference, str)
            and not reference.startswith("#/")
            and reference not in allowed_external
        ):
            raise RuntimeError("El schema de release usa una referencia no local.")
    return schema


@lru_cache(maxsize=1)
def release_validator() -> Draft202012Validator:
    content_schema = json.loads(CONTENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        CONTENT_SCHEMA_ID, Resource.from_contents(content_schema)
    )
    return Draft202012Validator(
        release_schema(),
        format_checker=FormatChecker(),
        registry=registry,
    )


def validate_release_snapshot(snapshot: object) -> None:
    try:
        release_validator().validate(snapshot)
    except JsonSchemaValidationError as error:
        path = ".".join(str(part) for part in error.absolute_path) or "snapshot"
        raise ReleaseSnapshotInvalid(
            f"El snapshot no cumple el schema en {path}."
        ) from error
