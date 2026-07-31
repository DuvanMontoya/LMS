# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import re
from collections.abc import Collection
from decimal import Decimal, InvalidOperation

from ..exceptions import AssessmentInvalid
from .limits import (
    MAX_INTEGER_EXPONENT_ABS,
    MAX_MATH_SYMBOLS,
    MAX_MATHJSON_DEPTH,
    MAX_MATHJSON_NODES,
    MAX_NUMBER_DIGITS,
    MAX_VARIADIC_ARGUMENTS,
)

type MathJson = int | str | list[MathJson]

SYMBOL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
CONSTANTS = frozenset({"Pi", "ExponentialE"})
BASE_OPERATORS = frozenset(
    {
        "Rational",
        "Add",
        "Subtract",
        "Negate",
        "Multiply",
        "Divide",
        "Power",
        "Sqrt",
        "Root",
        "Abs",
    }
)
OPTIONAL_FUNCTIONS = frozenset({"Sin", "Cos", "Tan", "Exp", "Ln", "Log"})
OPERATOR_ARITY: dict[str, tuple[int, int]] = {
    "Rational": (2, 2),
    "Add": (2, MAX_VARIADIC_ARGUMENTS),
    "Subtract": (2, 2),
    "Negate": (1, 1),
    "Multiply": (2, MAX_VARIADIC_ARGUMENTS),
    "Divide": (2, 2),
    "Power": (2, 2),
    "Sqrt": (1, 1),
    "Root": (2, 2),
    "Abs": (1, 1),
    "Sin": (1, 1),
    "Cos": (1, 1),
    "Tan": (1, 1),
    "Exp": (1, 1),
    "Ln": (1, 1),
    "Log": (1, 2),
}


def _validate_number(value: int | str) -> None:
    text = str(value)
    if not DECIMAL_PATTERN.fullmatch(text):
        raise AssessmentInvalid("MathJSON contiene un literal no permitido.")
    digits = text.lstrip("-").replace(".", "")
    if len(digits) > MAX_NUMBER_DIGITS:
        raise AssessmentInvalid("MathJSON contiene un número demasiado grande.")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise AssessmentInvalid("MathJSON contiene un número inválido.") from error
    if not number.is_finite():
        raise AssessmentInvalid("MathJSON contiene un número no finito.")


def validate_mathjson(
    value: object,
    *,
    allowed_symbols: Collection[str],
    allowed_functions: Collection[str],
) -> MathJson:
    symbols = frozenset(allowed_symbols)
    functions = frozenset(allowed_functions)
    if len(symbols) > MAX_MATH_SYMBOLS or any(
        not SYMBOL_PATTERN.fullmatch(symbol) for symbol in symbols
    ):
        raise AssessmentInvalid("La lista de símbolos matemáticos no es válida.")
    if not functions.issubset(OPTIONAL_FUNCTIONS):
        raise AssessmentInvalid("La lista de funciones matemáticas no es válida.")

    seen_symbols: set[str] = set()
    pending: list[tuple[object, int, str | None]] = [(value, 1, None)]
    node_count = 0
    while pending:
        current, depth, parent_operator = pending.pop()
        node_count += 1
        if node_count > MAX_MATHJSON_NODES:
            raise AssessmentInvalid("MathJSON supera el máximo de 200 nodos.")
        if depth > MAX_MATHJSON_DEPTH:
            raise AssessmentInvalid("MathJSON supera la profundidad máxima.")
        if isinstance(current, bool) or isinstance(current, float) or current is None:
            raise AssessmentInvalid("MathJSON contiene un literal no permitido.")
        if isinstance(current, int):
            _validate_number(current)
            if parent_operator == "Power" and abs(current) > MAX_INTEGER_EXPONENT_ABS:
                raise AssessmentInvalid("El exponente entero está fuera del límite.")
            continue
        if isinstance(current, str):
            if DECIMAL_PATTERN.fullmatch(current):
                _validate_number(current)
                continue
            if current in CONSTANTS:
                continue
            if not SYMBOL_PATTERN.fullmatch(current) or current not in symbols:
                raise AssessmentInvalid("MathJSON usa un símbolo no autorizado.")
            seen_symbols.add(current)
            if len(seen_symbols) > MAX_MATH_SYMBOLS:
                raise AssessmentInvalid("MathJSON usa demasiados símbolos.")
            continue
        if not isinstance(current, list) or not current:
            raise AssessmentInvalid("MathJSON sólo admite la representación corta.")
        operator = current[0]
        if not isinstance(operator, str):
            raise AssessmentInvalid("El operador MathJSON debe ser explícito.")
        if operator not in BASE_OPERATORS and operator not in functions:
            raise AssessmentInvalid("MathJSON usa un operador no autorizado.")
        minimum, maximum = OPERATOR_ARITY[operator]
        argument_count = len(current) - 1
        if argument_count < minimum or argument_count > maximum:
            raise AssessmentInvalid("El operador MathJSON tiene aridad inválida.")
        if operator == "Power":
            exponent = current[2]
            if not isinstance(exponent, int) or isinstance(exponent, bool):
                raise AssessmentInvalid(
                    "Sólo se admiten exponentes enteros explícitos y acotados."
                )
        if operator == "Root":
            root = current[2]
            if (
                not isinstance(root, int)
                or isinstance(root, bool)
                or root == 0
                or abs(root) > MAX_INTEGER_EXPONENT_ABS
            ):
                raise AssessmentInvalid("El índice de raíz debe ser entero y acotado.")
        if operator == "Rational":
            numerator, denominator = current[1:]
            if (
                not isinstance(numerator, int)
                or isinstance(numerator, bool)
                or not isinstance(denominator, int)
                or isinstance(denominator, bool)
                or denominator == 0
            ):
                raise AssessmentInvalid(
                    "Rational exige dos enteros y denominador no cero."
                )
        for argument in reversed(current[1:]):
            pending.append((argument, depth + 1, operator))
    return value  # type: ignore[return-value]


def _canonical_scalar(value: int | str) -> tuple[str, str]:
    if isinstance(value, int):
        return ("number", str(value))
    if DECIMAL_PATTERN.fullmatch(value):
        number = Decimal(value)
        normalized = format(number.normalize(), "f")
        if normalized == "-0":
            normalized = "0"
        return ("number", normalized)
    if value in CONSTANTS:
        return ("constant", value)
    return ("symbol", value)


def canonical_mathjson(value: MathJson) -> tuple[object, ...]:
    if isinstance(value, (int, str)):
        return _canonical_scalar(value)
    operator = value[0]
    arguments = tuple(canonical_mathjson(argument) for argument in value[1:])
    return ("operation", operator, *arguments)
