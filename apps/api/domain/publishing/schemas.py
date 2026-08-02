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

CURRENT_RELEASE_SCHEMA_VERSION = 3
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_ROOT = REPOSITORY_ROOT / "schemas"


def _walk(value: object):
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            yield current
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


@lru_cache(maxsize=3)
def release_schema(version: int) -> dict[str, Any]:
    schema = json.loads(
        (
            SCHEMA_ROOT / "publication" / f"course-release-v{version}.schema.json"
        ).read_text(encoding="utf-8")
    )
    content_version = min(version, 2)
    content_schema_id = f"urn:lms:content:unit-document:{content_version}"
    content_schema = json.loads(
        (
            SCHEMA_ROOT / "content" / f"unit-document-v{content_version}.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(content_schema)
    allowed_external = {content_schema_id}
    for item in _walk(schema):
        reference = item.get("$ref")
        if (
            isinstance(reference, str)
            and not reference.startswith("#/")
            and reference not in allowed_external
        ):
            raise RuntimeError("El schema de release usa una referencia no local.")
    return schema


@lru_cache(maxsize=3)
def release_validator(version: int) -> Draft202012Validator:
    content_version = min(version, 2)
    content_schema_id = f"urn:lms:content:unit-document:{content_version}"
    content_schema = json.loads(
        (
            SCHEMA_ROOT / "content" / f"unit-document-v{content_version}.schema.json"
        ).read_text(encoding="utf-8")
    )
    registry = Registry().with_resource(
        content_schema_id, Resource.from_contents(content_schema)
    )
    return Draft202012Validator(
        release_schema(version),
        format_checker=FormatChecker(),
        registry=registry,
    )


def validate_release_snapshot(snapshot: object) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") not in {
        1,
        2,
        3,
    }:
        raise ReleaseSnapshotInvalid("La versión del snapshot no está soportada.")
    version = int(snapshot["schema_version"])
    try:
        release_validator(version).validate(snapshot)
    except JsonSchemaValidationError as error:
        path = ".".join(str(part) for part in error.absolute_path) or "snapshot"
        raise ReleaseSnapshotInvalid(
            f"El snapshot no cumple el schema en {path}."
        ) from error
