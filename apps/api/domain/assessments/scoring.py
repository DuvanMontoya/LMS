# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnnecessaryComparison=false
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from types import MappingProxyType
from typing import Any, Literal, cast

from .choices import QuestionType
from .exceptions import AssessmentInvalid
from .math import canonical_mathjson, validate_mathjson
from .math.equivalence import MathEquivalenceOutcome

SCORING_ENGINE_VERSION = 2
SCORE_QUANTUM = Decimal("0.001")
MAX_NUMERIC_TEXT_LENGTH = 120
MAX_SIGNIFICANT_DIGITS = 100
MAX_ADJUSTED_EXPONENT = 100
DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
WHITESPACE_PATTERN = re.compile(r"\s+")

ScoringStatus = Literal["scored", "pending_manual"]

LEGACY_SCORING_POLICIES: Mapping[str, str] = MappingProxyType(
    {
        QuestionType.SINGLE_CHOICE: "all_or_nothing",
        QuestionType.MULTIPLE_CHOICE: "exact_set",
        QuestionType.TRUE_FALSE: "all_or_nothing",
        QuestionType.NUMERIC: "binary_tolerance",
        QuestionType.SHORT_TEXT: "all_or_nothing",
        QuestionType.LONG_TEXT: "manual",
        QuestionType.ORDERING: "exact",
        QuestionType.MATCHING: "exact",
    }
)

ALLOWED_POLICIES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        QuestionType.SINGLE_CHOICE: frozenset({"all_or_nothing"}),
        QuestionType.MULTIPLE_CHOICE: frozenset(
            {"exact_set", "proportional_with_penalty"}
        ),
        QuestionType.TRUE_FALSE: frozenset({"all_or_nothing"}),
        QuestionType.NUMERIC: frozenset({"binary_tolerance", "banded_tolerance"}),
        QuestionType.SHORT_TEXT: frozenset({"all_or_nothing"}),
        QuestionType.LONG_TEXT: frozenset({"manual"}),
        QuestionType.ORDERING: frozenset(
            {"exact", "position_fraction", "adjacent_pair_fraction"}
        ),
        QuestionType.MATCHING: frozenset({"exact", "per_pair"}),
        QuestionType.MATHEMATICAL_EXPRESSION: frozenset(
            {"structural", "symbolic_common_domain"}
        ),
    }
)


@dataclass(frozen=True)
class ScoringResult:
    status: ScoringStatus
    credit_basis_points: int
    raw_score: Decimal
    score: Decimal
    maximum_score: Decimal
    is_correct: bool | None
    normalized_response: object
    feedback_key: str
    manual_review_reason: str = ""
    diagnostics: Mapping[str, bool | int | str] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def requires_manual(self) -> bool:
        return self.status == "pending_manual"


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


def _fraction_basis_points(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise AssessmentInvalid("La policy de scoring tiene denominador inválido.")
    return (numerator * 10000) // denominator


def _validate_credit(value: int) -> int:
    if value < 0 or value > 10000:
        raise AssessmentInvalid("El crédito debe estar entre 0 y 10000 basis points.")
    return value


def _result(
    *,
    credit: int,
    maximum: Decimal,
    normalized_response: object,
    status: ScoringStatus = "scored",
    manual_review_reason: str = "",
    diagnostics: Mapping[str, bool | int | str] | None = None,
) -> ScoringResult:
    credit = _validate_credit(credit)
    if maximum < 0 or not maximum.is_finite():
        raise AssessmentInvalid("El puntaje máximo no puede ser negativo.")
    with localcontext() as context:
        context.prec = 50
        raw_score = (maximum * Decimal(credit)) / Decimal(10000)
    score = quantize_score(raw_score)
    if score < 0 or score > quantize_score(maximum):
        raise AssessmentInvalid("El puntaje calculado está fuera del máximo.")
    return ScoringResult(
        status=status,
        credit_basis_points=credit,
        raw_score=raw_score,
        score=score,
        maximum_score=quantize_score(maximum),
        is_correct=(credit == 10000 if status == "scored" else None),
        normalized_response=normalized_response,
        feedback_key=(
            "pending_manual"
            if status == "pending_manual"
            else "correct"
            if credit == 10000
            else "incorrect"
            if credit == 0
            else "partial"
        ),
        manual_review_reason=manual_review_reason,
        diagnostics=MappingProxyType(dict(diagnostics or {})),
    )


def _multiple_choice_credit(
    policy: str, grading: Mapping[str, Any], value: object
) -> tuple[int, list[str]]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssessmentInvalid("La respuesta múltiple debe ser una lista de IDs.")
    submitted_list = cast(list[str], value)
    if len(submitted_list) != len(set(submitted_list)):
        raise AssessmentInvalid("La respuesta múltiple contiene IDs repetidos.")
    submitted = set(submitted_list)
    correct = set(cast(list[str], grading["correct_option_ids"]))
    option_ids = set(cast(list[str], grading.get("option_ids", list(correct))))
    if not submitted.issubset(option_ids):
        raise AssessmentInvalid(
            "La respuesta múltiple contiene una opción desconocida."
        )
    if policy == "exact_set":
        return (10000 if submitted == correct else 0), sorted(submitted)
    incorrect = option_ids - correct
    if not correct or not incorrect:
        raise AssessmentInvalid(
            "La policy proporcional exige opciones correctas e incorrectas."
        )
    true_positive = len(submitted & correct)
    false_positive = len(submitted & incorrect)
    with localcontext() as context:
        context.prec = 50
        fraction = max(
            Decimal("0"),
            Decimal(true_positive) / Decimal(len(correct))
            - Decimal(false_positive) / Decimal(len(incorrect)),
        )
        credit = int(
            (fraction * Decimal(10000)).to_integral_value(rounding=ROUND_FLOOR)
        )
    return credit, sorted(submitted)


def _ordering_credit(
    policy: str, grading: Mapping[str, Any], value: object
) -> tuple[int, list[str]]:
    expected = cast(list[str], grading["correct_order"])
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) for item in value)
        or len(value) != len(set(value))
        or set(value) != set(expected)
    ):
        raise AssessmentInvalid(
            "La respuesta de ordenamiento no es una permutación válida."
        )
    submitted = cast(list[str], value)
    if policy == "exact":
        credit = 10000 if submitted == expected else 0
    elif policy == "position_fraction":
        credit = _fraction_basis_points(
            sum(left == right for left, right in zip(submitted, expected, strict=True)),
            len(expected),
        )
    else:
        if len(expected) < 2:
            raise AssessmentInvalid("La policy por pares exige al menos dos opciones.")
        expected_pairs = set(zip(expected, expected[1:], strict=False))
        submitted_pairs = set(zip(submitted, submitted[1:], strict=False))
        credit = _fraction_basis_points(
            len(expected_pairs & submitted_pairs), len(expected) - 1
        )
    return credit, submitted


def _matching_credit(
    policy: str, grading: Mapping[str, Any], value: object
) -> tuple[int, dict[str, str]]:
    expected = cast(dict[str, str], grading["correct_pairs"])
    if (
        not isinstance(value, dict)
        or any(
            not isinstance(key, str) or not isinstance(item, str)
            for key, item in value.items()
        )
        or set(value) != set(expected)
    ):
        raise AssessmentInvalid(
            "La respuesta de emparejamiento no cubre los pares válidos."
        )
    submitted = cast(dict[str, str], value)
    allowed_right = set(expected.values())
    if not set(submitted.values()).issubset(allowed_right):
        raise AssessmentInvalid(
            "La respuesta usa una opción de emparejamiento desconocida."
        )
    correct = sum(submitted[key] == expected[key] for key in expected)
    credit = (
        10000
        if policy == "exact" and correct == len(expected)
        else 0
        if policy == "exact"
        else _fraction_basis_points(correct, len(expected))
    )
    return credit, dict(sorted(submitted.items()))


def _numeric_credit(
    policy: str, grading: Mapping[str, Any], value: object
) -> tuple[int, str]:
    submitted = parse_decimal_text(value)
    expected = parse_decimal_text(grading["correct_value"])
    full_tolerance = parse_decimal_text(
        grading.get("full_tolerance", grading.get("tolerance"))
    )
    if full_tolerance < 0:
        raise AssessmentInvalid("La tolerancia no puede ser negativa.")
    difference = abs(submitted - expected)
    if policy == "binary_tolerance":
        return (10000 if difference <= full_tolerance else 0), format(submitted, "f")
    partial_tolerance = parse_decimal_text(grading["partial_tolerance"])
    partial_credit = _validate_credit(int(grading["partial_credit_basis_points"]))
    if partial_tolerance <= full_tolerance or partial_credit in {0, 10000}:
        raise AssessmentInvalid("Las bandas de tolerancia no son válidas.")
    if difference <= full_tolerance:
        credit = 10000
    elif difference <= partial_tolerance:
        credit = partial_credit
    else:
        credit = 0
    return credit, format(submitted, "f")


def _math_result(
    *,
    policy: str,
    grading: Mapping[str, Any],
    value: object,
    maximum: Decimal,
    symbolic_outcome: MathEquivalenceOutcome | None,
) -> ScoringResult:
    if not isinstance(value, dict) or set(value) != {"latex", "mathjson"}:
        raise AssessmentInvalid(
            "La respuesta matemática no tiene el contrato esperado."
        )
    latex = value["latex"]
    if (
        not isinstance(latex, str)
        or not latex
        or len(latex) > int(grading.get("maximum_latex_length", 4096))
    ):
        raise AssessmentInvalid("La representación LaTeX no tiene una longitud válida.")
    symbols = cast(list[str], grading["allowed_symbols"])
    functions = cast(list[str], grading["allowed_functions"])
    submitted = validate_mathjson(
        value["mathjson"],
        allowed_symbols=symbols,
        allowed_functions=functions,
    )
    expected = validate_mathjson(
        grading["expected_mathjson"],
        allowed_symbols=symbols,
        allowed_functions=functions,
    )
    normalized = {"latex": latex, "mathjson": submitted}
    if policy == "structural":
        return _result(
            credit=(
                10000
                if canonical_mathjson(submitted) == canonical_mathjson(expected)
                else 0
            ),
            maximum=maximum,
            normalized_response=normalized,
        )
    if symbolic_outcome is None:
        return _result(
            credit=0,
            maximum=maximum,
            normalized_response=normalized,
            status="pending_manual",
            manual_review_reason="symbolic_grading_required",
        )
    if symbolic_outcome.status == "inconclusive":
        return _result(
            credit=0,
            maximum=maximum,
            normalized_response=normalized,
            status="pending_manual",
            manual_review_reason="symbolic_inconclusive",
            diagnostics={"counterexample_found": symbolic_outcome.counterexample_found},
        )
    return _result(
        credit=10000 if symbolic_outcome.status == "equivalent" else 0,
        maximum=maximum,
        normalized_response=normalized,
        diagnostics={"counterexample_found": symbolic_outcome.counterexample_found},
    )


def score_question(
    *,
    question_type: str,
    grading: dict[str, Any],
    response: dict[str, Any],
    maximum: Decimal,
    scoring_policy: str | None = None,
    symbolic_outcome: MathEquivalenceOutcome | None = None,
) -> ScoringResult:
    policy = scoring_policy or LEGACY_SCORING_POLICIES.get(question_type)
    if policy is None or policy not in ALLOWED_POLICIES.get(question_type, frozenset()):
        raise AssessmentInvalid("La policy no corresponde al tipo de pregunta.")
    if response.get("type") != question_type:
        raise AssessmentInvalid("La respuesta pertenece a otro tipo de pregunta.")
    value = response.get("value")
    if _empty(value):
        return _result(
            credit=0,
            maximum=maximum,
            normalized_response=value,
        )
    if question_type == QuestionType.SINGLE_CHOICE:
        credit = 10000 if value == grading["correct_option_ids"][0] else 0
        normalized: object = value
    elif question_type == QuestionType.MULTIPLE_CHOICE:
        credit, normalized = _multiple_choice_credit(policy, grading, value)
    elif question_type == QuestionType.TRUE_FALSE:
        credit = (
            10000
            if isinstance(value, bool) and value is grading["correct_boolean"]
            else 0
        )
        normalized = value
    elif question_type == QuestionType.NUMERIC:
        credit, normalized = _numeric_credit(policy, grading, value)
    elif question_type == QuestionType.SHORT_TEXT:
        case_sensitive = bool(grading["case_sensitive"])
        normalized = normalize_short_text(value, case_sensitive=case_sensitive)
        accepted = {
            normalize_short_text(item, case_sensitive=case_sensitive)
            for item in grading["accepted_answers"]
        }
        credit = 10000 if normalized in accepted else 0
    elif question_type == QuestionType.LONG_TEXT:
        return _result(
            credit=0,
            maximum=maximum,
            normalized_response=value,
            status="pending_manual",
            manual_review_reason="long_text",
        )
    elif question_type == QuestionType.ORDERING:
        credit, normalized = _ordering_credit(policy, grading, value)
    elif question_type == QuestionType.MATCHING:
        credit, normalized = _matching_credit(policy, grading, value)
    elif question_type == QuestionType.MATHEMATICAL_EXPRESSION:
        return _math_result(
            policy=policy,
            grading=grading,
            value=value,
            maximum=maximum,
            symbolic_outcome=symbolic_outcome,
        )
    else:
        raise AssessmentInvalid("El tipo de pregunta no tiene calificador registrado.")
    return _result(
        credit=credit,
        maximum=maximum,
        normalized_response=normalized,
    )


def basis_points(*, score: Decimal, maximum: Decimal) -> int:
    if maximum <= 0:
        return 0
    with localcontext() as context:
        context.prec = 50
        value = (score * Decimal("10000")) / maximum
        return min(
            10000,
            max(0, int(value.to_integral_value(rounding=ROUND_FLOOR))),
        )
