# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from referencing import Registry, Resource

from .canonical import canonical_json_bytes, deep_json_copy
from .exceptions import AssessmentInvalid
from .limits import MAX_QUESTION_DEFINITION_BYTES, MAX_RESPONSE_BYTES
from .math import validate_mathjson
from .scoring import normalize_short_text, parse_decimal_text

CURRENT_ASSESSMENT_SCHEMA_VERSION = 1
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_ROOT = REPOSITORY_ROOT / "schemas"
CONTENT_SCHEMA_V1_ID = "urn:lms:content:unit-document:1"
CONTENT_SCHEMA_V2_ID = "urn:lms:content:unit-document:2"
QUESTION_PUBLIC_SCHEMA_ID = "urn:lms:assessment:question-public:1"
QUESTION_DEFINITION_SCHEMA_ID = "urn:lms:assessment:question-definition:1"
RESPONSE_SCHEMA_ID = "urn:lms:assessment:response:1"
ASSESSMENT_VERSION_SCHEMA_ID = "urn:lms:assessment:assessment-version:1"
MATH_EXPRESSION_SCHEMA_ID = "urn:lms:assessment:math-expression:1"
MATH_EXPRESSION_RESPONSE_SCHEMA_ID = "urn:lms:assessment:math-expression-response:1"
SCORING_POLICY_SCHEMA_ID = "urn:lms:assessment:scoring-policy:2"
GRADING_REVISION_SCHEMA_ID = "urn:lms:assessment:grading-revision:1"

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_MATH = re.compile(
    r"(?:\\(?:require|style|class|cssId|htmlClass|htmlId|htmlStyle|href)\b|"
    r"<\s*/?\s*tex-html\b|javascript\s*:|data\s*:)",
    re.IGNORECASE,
)

SCHEMA_PATHS = {
    CONTENT_SCHEMA_V1_ID: SCHEMA_ROOT / "content" / "unit-document-v1.schema.json",
    CONTENT_SCHEMA_V2_ID: SCHEMA_ROOT / "content" / "unit-document-v2.schema.json",
    QUESTION_PUBLIC_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "question-public-v1.schema.json"
    ),
    QUESTION_DEFINITION_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "question-definition-v1.schema.json"
    ),
    RESPONSE_SCHEMA_ID: SCHEMA_ROOT / "assessment" / "response-v1.schema.json",
    ASSESSMENT_VERSION_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "assessment-version-v1.schema.json"
    ),
    MATH_EXPRESSION_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "math-expression-v1.schema.json"
    ),
    MATH_EXPRESSION_RESPONSE_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "math-expression-response-v1.schema.json"
    ),
    SCORING_POLICY_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "scoring-policy-v2.schema.json"
    ),
    GRADING_REVISION_SCHEMA_ID: (
        SCHEMA_ROOT / "assessment" / "grading-revision-v1.schema.json"
    ),
}


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
def schema_documents() -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for schema_id, path in SCHEMA_PATHS.items():
        document = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(document)
        if document.get("$id") != schema_id:
            raise RuntimeError(f"El schema {path.name} no conserva su identificador.")
        documents[schema_id] = document

    allowed = set(documents)
    for schema_id, document in documents.items():
        for item in _walk(document):
            reference = item.get("$ref")
            if (
                isinstance(reference, str)
                and not reference.startswith("#")
                and reference not in allowed
            ):
                raise RuntimeError(
                    f"El schema {schema_id} usa una referencia externa no permitida."
                )
    return documents


@lru_cache(maxsize=1)
def schema_registry() -> Registry:
    registry = Registry()
    for schema_id, document in schema_documents().items():
        registry = registry.with_resource(schema_id, Resource.from_contents(document))
    return registry


@lru_cache(maxsize=8)
def validator_for(schema_id: str) -> Draft202012Validator:
    document = schema_documents().get(schema_id)
    if document is None:
        raise AssessmentInvalid("La versión del contrato no está soportada.")
    return Draft202012Validator(
        document,
        format_checker=FormatChecker(),
        registry=schema_registry(),
    )


def _validate(payload: object, schema_id: str, *, field: str) -> dict[str, Any]:
    try:
        copied = deep_json_copy(payload)
    except (TypeError, ValueError, OverflowError) as copy_error:
        raise AssessmentInvalid(
            "El valor debe contener únicamente JSON válido.", path=field
        ) from copy_error
    if not isinstance(copied, dict):
        raise AssessmentInvalid("La raíz debe ser un objeto.", path=field)
    errors = sorted(
        validator_for(schema_id).iter_errors(copied),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        error: JsonSchemaValidationError = errors[0]
        suffix = ".".join(str(item) for item in error.absolute_path)
        path = f"{field}.{suffix}" if suffix else field
        raise AssessmentInvalid(
            "El valor no cumple el contrato JSON Schema.", path=path
        )
    return copied


def _identifiers(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    return [
        str(item["id"]) for item in items if isinstance(item, dict) and "id" in item
    ]


def _validate_prompt_legacy_nodes(prompt: object) -> None:
    copied = deep_json_copy(prompt)
    if not isinstance(copied, dict) or not isinstance(copied.get("content"), list):
        return
    asset_types = {
        "imageAsset",
        "audioAsset",
        "videoAsset",
        "documentAsset",
        "datasetAsset",
    }
    legacy_blocks: list[object] = []
    for block in copied["content"]:
        if isinstance(block, dict) and block.get("type") in asset_types:
            attrs = block.get("attrs")
            node_id = attrs.get("nodeId") if isinstance(attrs, dict) else None
            legacy_blocks.append({"type": "paragraph", "attrs": {"nodeId": node_id}})
        else:
            legacy_blocks.append(block)
    legacy = {"type": "doc", "content": legacy_blocks}
    errors = sorted(
        validator_for(CONTENT_SCHEMA_V1_ID).iter_errors(legacy),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        raise AssessmentInvalid(
            "Los nodos semánticos heredados del enunciado son inválidos.",
            path="definition.public.prompt",
        )


def _validate_definition_math(definition: dict[str, Any]) -> None:
    public = definition["public"]
    candidates: list[tuple[str, str]] = []
    for node in _walk(public.get("prompt")):
        if node.get("type") not in {"inlineMath", "displayMath"}:
            continue
        attrs = node.get("attrs")
        if isinstance(attrs, dict) and isinstance(attrs.get("latex"), str):
            candidates.append(("definition.public.prompt", attrs["latex"]))
    for collection_name in ("options", "left", "right"):
        collection = public.get(collection_name)
        if not isinstance(collection, list):
            continue
        for index, option in enumerate(collection):
            if isinstance(option, dict) and isinstance(option.get("math_latex"), str):
                candidates.append(
                    (
                        f"definition.public.{collection_name}.{index}.math_latex",
                        option["math_latex"],
                    )
                )
    worked_solution = definition.get("worked_solution")
    if isinstance(worked_solution, dict):
        for node in _walk(worked_solution):
            if node.get("type") not in {"inlineMath", "displayMath"}:
                continue
            attrs = node.get("attrs")
            if isinstance(attrs, dict) and isinstance(attrs.get("latex"), str):
                candidates.append(("definition.worked_solution", attrs["latex"]))
    for path, latex in candidates:
        if _CONTROL_CHARACTERS.search(latex) or _UNSAFE_MATH.search(latex):
            raise AssessmentInvalid(
                "La fórmula contiene una capacidad no permitida.", path=path
            )


def _validate_definition_semantics(definition: dict[str, Any]) -> None:
    question_type = str(definition["type"])
    public = definition["public"]
    grading = definition["grading"]
    _validate_prompt_legacy_nodes(public["prompt"])
    if "worked_solution" in definition:
        _validate_prompt_legacy_nodes(definition["worked_solution"])
    _validate_definition_math(definition)
    if public["type"] != question_type:
        raise AssessmentInvalid(
            "El tipo público debe coincidir con el tipo de la pregunta.",
            path="definition.public.type",
        )

    if question_type in {
        "single_choice",
        "multiple_choice",
        "ordering",
    }:
        option_ids = _identifiers(public["options"])
        if len(option_ids) != len(set(option_ids)):
            raise AssessmentInvalid(
                "Los identificadores de opción deben ser únicos.",
                path="definition.public.options",
            )
        authoring = definition.get("authoring")
        rationales = (
            authoring.get("choice_rationales") if isinstance(authoring, dict) else None
        )
        if isinstance(rationales, dict) and not set(rationales).issubset(option_ids):
            raise AssessmentInvalid(
                "El análisis de distractores sólo puede referenciar opciones existentes.",
                path="definition.authoring.choice_rationales",
            )
        key = (
            grading["correct_order"]
            if question_type == "ordering"
            else grading["correct_option_ids"]
        )
        if question_type == "ordering":
            valid = len(key) == len(option_ids) and set(key) == set(option_ids)
        else:
            valid = set(key).issubset(option_ids)
        if not valid:
            raise AssessmentInvalid(
                "La clave debe referenciar exactamente opciones públicas válidas.",
                path="definition.grading",
            )

    if question_type == "single_choice":
        if len(grading["correct_option_ids"]) != 1:
            raise AssessmentInvalid(
                "La selección única exige una sola opción correcta.",
                path="definition.grading.correct_option_ids",
            )

    if question_type == "matching":
        left = _identifiers(public["left"])
        right = _identifiers(public["right"])
        pairs = grading["correct_pairs"]
        if (
            len(left) != len(set(left))
            or len(right) != len(set(right))
            or set(pairs) != set(left)
            or not set(pairs.values()).issubset(right)
        ):
            raise AssessmentInvalid(
                "La clave de emparejamiento debe cubrir el lado izquierdo y usar el derecho.",
                path="definition.grading.correct_pairs",
            )

    if question_type == "numeric":
        parse_decimal_text(grading["correct_value"])
        tolerance = parse_decimal_text(grading["tolerance"])
        if tolerance < 0:
            raise AssessmentInvalid(
                "La tolerancia no puede ser negativa.",
                path="definition.grading.tolerance",
            )

    if question_type == "short_text":
        case_sensitive = bool(grading["case_sensitive"])
        normalized = [
            normalize_short_text(value, case_sensitive=case_sensitive)
            for value in grading["accepted_answers"]
        ]
        if any(not value for value in normalized):
            raise AssessmentInvalid(
                "Una respuesta aceptada no puede quedar vacía al normalizarse.",
                path="definition.grading.accepted_answers",
            )
        if len(normalized) != len(set(normalized)):
            raise AssessmentInvalid(
                "Las respuestas aceptadas colisionan después de normalizarse.",
                path="definition.grading.accepted_answers",
            )

    if question_type == "mathematical_expression":
        public_symbols = public["allowed_symbols"]
        grading_symbols = grading["allowed_symbols"]
        public_functions = public["allowed_functions"]
        grading_functions = grading["allowed_functions"]
        if public_symbols != grading_symbols or public_functions != grading_functions:
            raise AssessmentInvalid(
                "Los símbolos y funciones públicos deben coincidir con grading.",
                path="definition.grading",
            )
        assumptions = grading["symbol_assumptions"]
        if not set(assumptions).issubset(set(grading_symbols)):
            raise AssessmentInvalid(
                "Las assumptions usan un símbolo no autorizado.",
                path="definition.grading.symbol_assumptions",
            )
        for symbol, declared in assumptions.items():
            if "positive" in declared and "nonnegative" in declared:
                raise AssessmentInvalid(
                    "Positive ya implica nonnegative; declare sólo la más específica.",
                    path=f"definition.grading.symbol_assumptions.{symbol}",
                )
        validate_mathjson(
            grading["expected_mathjson"],
            allowed_symbols=grading_symbols,
            allowed_functions=grading_functions,
        )


def validate_question_definition(payload: object) -> dict[str, Any]:
    if len(canonical_json_bytes(payload)) > MAX_QUESTION_DEFINITION_BYTES:
        raise AssessmentInvalid("La definición supera 1 MiB.", path="definition")
    definition = _validate(payload, QUESTION_DEFINITION_SCHEMA_ID, field="definition")
    _validate_definition_semantics(definition)
    return definition


def validate_public_question(payload: object) -> dict[str, Any]:
    return _validate(payload, QUESTION_PUBLIC_SCHEMA_ID, field="public")


def validate_response(payload: object, *, expected_type: str) -> dict[str, Any]:
    if len(canonical_json_bytes(payload)) > MAX_RESPONSE_BYTES:
        raise AssessmentInvalid("La respuesta supera 64 KiB.", path="response")
    response = _validate(payload, RESPONSE_SCHEMA_ID, field="response")
    if response["type"] != expected_type:
        raise AssessmentInvalid(
            "El tipo de respuesta no coincide con la pregunta.",
            path="response.type",
        )
    return response


def validate_assessment_snapshot(payload: object) -> dict[str, Any]:
    return _validate(payload, ASSESSMENT_VERSION_SCHEMA_ID, field="public_snapshot")


def validate_scoring_policy(payload: object) -> dict[str, Any]:
    return _validate(payload, SCORING_POLICY_SCHEMA_ID, field="scoring_policy")


def validate_grading_revision_snapshot(payload: object) -> dict[str, Any]:
    return _validate(payload, GRADING_REVISION_SCHEMA_ID, field="grading_snapshot")


def validate_schema_contracts() -> None:
    schema_documents.cache_clear()
    schema_registry.cache_clear()
    validator_for.cache_clear()
    for schema_id in SCHEMA_PATHS:
        validator_for(schema_id)
