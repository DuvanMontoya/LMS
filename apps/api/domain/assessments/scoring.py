from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from types import MappingProxyType
from typing import Any, cast

from .choices import QuestionType
from .exceptions import AssessmentInvalid

SCORE_QUANTUM = Decimal("0.001")
MAX_NUMERIC_TEXT_LENGTH = 120
MAX_SIGNIFICANT_DIGITS = 100
MAX_ADJUSTED_EXPONENT = 100
DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class ScoringResult:
    score: Decimal
    requires_manual: bool


def quantize_score(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise AssessmentInvalid("El puntaje debe ser finito.")
    return value.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def parse_decimal_text(value: object) -> Decimal:
    if not isinstance(value, str):
        raise AssessmentInvalid("El valor numérico debe enviarse como texto.")
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_NUMERIC_TEXT_LENGTH:
        raise AssessmentInvalid("El valor numérico no tiene una longitud válida.")
    if "," in normalized:
        if "." in normalized or normalized.count(",") != 1:
            raise AssessmentInvalid("El separador decimal es ambiguo.")
        normalized = normalized.replace(",", ".")
    if not DECIMAL_PATTERN.fullmatch(normalized):
        raise AssessmentInvalid("El valor numérico no usa notación decimal válida.")
    digits = normalized.lstrip("-").replace(".", "").lstrip("0") or "0"
    if len(digits) > MAX_SIGNIFICANT_DIGITS:
        raise AssessmentInvalid("El valor numérico tiene demasiados dígitos.")
    try:
        with localcontext() as context:
            context.prec = MAX_SIGNIFICANT_DIGITS + 10
            parsed = Decimal(normalized)
    except InvalidOperation as error:
        raise AssessmentInvalid("El valor numérico no es representable.") from error
    if not parsed.is_finite() or abs(parsed.adjusted()) > MAX_ADJUSTED_EXPONENT:
        raise AssessmentInvalid("El valor numérico está fuera de rango.")
    return parsed


def normalize_short_text(value: object, *, case_sensitive: bool) -> str:
    if not isinstance(value, str):
        raise AssessmentInvalid("La respuesta corta debe ser texto.")
    normalized = unicodedata.normalize("NFC", value)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized.strip())
    return normalized if case_sensitive else normalized.casefold()


def _empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _binary(correct: bool, maximum: Decimal) -> ScoringResult:
    return ScoringResult(
        score=quantize_score(maximum if correct else Decimal("0")),
        requires_manual=False,
    )


def _single_choice(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    return _binary(
        value == grading["correct_option_ids"][0],
        maximum,
    )


def _multiple_choice(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    submitted: set[str] = set()
    if isinstance(value, list):
        submitted = {str(item) for item in cast(list[object], value)}
    return _binary(submitted == set(grading["correct_option_ids"]), maximum)


def _true_false(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    return _binary(
        isinstance(value, bool) and value is grading["correct_boolean"], maximum
    )


def _numeric(grading: dict[str, Any], value: object, maximum: Decimal) -> ScoringResult:
    submitted = parse_decimal_text(value)
    expected = parse_decimal_text(grading["correct_value"])
    tolerance = parse_decimal_text(grading["tolerance"])
    return _binary(abs(submitted - expected) <= tolerance, maximum)


def _short_text(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    case_sensitive = bool(grading["case_sensitive"])
    submitted = normalize_short_text(value, case_sensitive=case_sensitive)
    accepted = {
        normalize_short_text(item, case_sensitive=case_sensitive)
        for item in grading["accepted_answers"]
    }
    return _binary(submitted in accepted, maximum)


def _long_text(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    del grading, maximum
    return ScoringResult(score=Decimal("0.000"), requires_manual=not _empty(value))


def _ordering(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    return _binary(value == grading["correct_order"], maximum)


def _matching(
    grading: dict[str, Any], value: object, maximum: Decimal
) -> ScoringResult:
    return _binary(value == grading["correct_pairs"], maximum)


Scorer = Callable[[dict[str, Any], object, Decimal], ScoringResult]
SCORERS: MappingProxyType[str, Scorer] = MappingProxyType(
    {
        QuestionType.SINGLE_CHOICE: _single_choice,
        QuestionType.MULTIPLE_CHOICE: _multiple_choice,
        QuestionType.TRUE_FALSE: _true_false,
        QuestionType.NUMERIC: _numeric,
        QuestionType.SHORT_TEXT: _short_text,
        QuestionType.LONG_TEXT: _long_text,
        QuestionType.ORDERING: _ordering,
        QuestionType.MATCHING: _matching,
    }
)


def score_question(
    *,
    question_type: str,
    grading: dict[str, Any],
    response: dict[str, Any],
    maximum: Decimal,
) -> ScoringResult:
    if maximum < 0:
        raise AssessmentInvalid("El puntaje máximo no puede ser negativo.")
    if response.get("type") != question_type:
        raise AssessmentInvalid("La respuesta pertenece a otro tipo de pregunta.")
    value = response.get("value")
    if _empty(value):
        return ScoringResult(score=Decimal("0.000"), requires_manual=False)
    scorer = SCORERS.get(question_type)
    if scorer is None:
        raise AssessmentInvalid("El tipo de pregunta no tiene calificador registrado.")
    return scorer(grading, value, maximum)


def basis_points(*, score: Decimal, maximum: Decimal) -> int:
    if maximum <= 0:
        return 0
    with localcontext() as context:
        context.prec = 50
        value = (score * Decimal("10000")) / maximum
        return int(value.to_integral_value(rounding=ROUND_FLOOR))
