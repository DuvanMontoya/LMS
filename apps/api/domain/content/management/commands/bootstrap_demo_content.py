# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.content.models import UnitContentDocument
from domain.content.services import save_unit_content
from domain.courses.choices import EDITABLE_AUTHORING_STATUSES, StructureStatus
from domain.courses.models import Course, CourseUnit
from domain.identity.models import User
from domain.organizations.models import Organization

DEMO_COURSE_SLUG = "introduccion-calculo-diferencial"
DEMO_NAMESPACE = uuid.UUID("7994878c-71f4-4acc-b7c8-674534ff0b2a")


def _id(unit: CourseUnit, label: str) -> str:
    return str(uuid.uuid5(DEMO_NAMESPACE, f"{unit.id}:{label}"))


def _paragraph(unit: CourseUnit, label: str, text: str) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "attrs": {"nodeId": _id(unit, label)},
        "content": [{"type": "text", "text": text}],
    }


def _fallback_document(unit: CourseUnit) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            _paragraph(
                unit,
                "intro",
                f"{unit.title} se estudia aquí mediante explicaciones y ejemplos verificables.",
            )
        ],
    }


def _functions_document(unit: CourseUnit) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            _paragraph(
                unit,
                "intro",
                "Una función relaciona cada elemento de su dominio con un único valor de salida.",
            ),
            {
                "type": "pedagogicalBlock",
                "attrs": {
                    "nodeId": _id(unit, "definition"),
                    "kind": "definition",
                    "title": "Función",
                },
                "content": [
                    _paragraph(
                        unit,
                        "definition-paragraph",
                        "El dominio reúne las entradas admitidas y el rango los valores obtenidos.",
                    )
                ],
            },
            {
                "type": "paragraph",
                "attrs": {"nodeId": _id(unit, "inline-paragraph")},
                "content": [
                    {"type": "text", "text": "Por ejemplo, "},
                    {
                        "type": "inlineMath",
                        "attrs": {
                            "nodeId": _id(unit, "inline-math"),
                            "latex": "f(x)=x^2",
                        },
                    },
                    {"type": "text", "text": " asigna a cada número su cuadrado."},
                ],
            },
            {
                "type": "displayMath",
                "attrs": {
                    "nodeId": _id(unit, "display-math"),
                    "latex": "f(x)=x^2",
                    "label": "quadratic-function",
                },
            },
            {
                "type": "table",
                "attrs": {
                    "nodeId": _id(unit, "table"),
                    "caption": "Valores de la función cuadrática",
                },
                "content": [
                    {
                        "type": "tableRow",
                        "attrs": {"nodeId": _id(unit, "header-row")},
                        "content": [
                            {
                                "type": "tableHeader",
                                "attrs": {
                                    "nodeId": _id(unit, "header-x"),
                                    "colspan": 1,
                                    "rowspan": 1,
                                    "colwidth": None,
                                },
                                "content": [_paragraph(unit, "header-x-p", "x")],
                            },
                            {
                                "type": "tableHeader",
                                "attrs": {
                                    "nodeId": _id(unit, "header-fx"),
                                    "colspan": 1,
                                    "rowspan": 1,
                                    "colwidth": None,
                                },
                                "content": [_paragraph(unit, "header-fx-p", "f(x)")],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "attrs": {"nodeId": _id(unit, "body-row")},
                        "content": [
                            {
                                "type": "tableCell",
                                "attrs": {
                                    "nodeId": _id(unit, "cell-x"),
                                    "colspan": 1,
                                    "rowspan": 1,
                                    "colwidth": None,
                                },
                                "content": [_paragraph(unit, "cell-x-p", "2")],
                            },
                            {
                                "type": "tableCell",
                                "attrs": {
                                    "nodeId": _id(unit, "cell-fx"),
                                    "colspan": 1,
                                    "rowspan": 1,
                                    "colwidth": None,
                                },
                                "content": [_paragraph(unit, "cell-fx-p", "4")],
                            },
                        ],
                    },
                ],
            },
            {
                "type": "codeBlock",
                "attrs": {
                    "nodeId": _id(unit, "code"),
                    "language": "python",
                    "caption": "Implementación de la función cuadrática",
                    "code": "def f(x: float) -> float:\n    return x**2",
                },
            },
        ],
    }


def _limit_document(unit: CourseUnit) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            _paragraph(
                unit,
                "intro",
                "Un límite describe el valor al que se aproxima una función cuando su entrada se acerca a un punto.",
            ),
            {
                "type": "displayMath",
                "attrs": {
                    "nodeId": _id(unit, "limit"),
                    "latex": r"\lim_{x\to a}f(x)=L",
                    "label": "limit-notation",
                },
            },
            {
                "type": "pedagogicalBlock",
                "attrs": {
                    "nodeId": _id(unit, "example"),
                    "kind": "example",
                    "title": "Acercamiento numérico",
                },
                "content": [
                    _paragraph(
                        unit,
                        "example-p",
                        "Se comparan valores por ambos lados sin afirmar que la función deba estar definida en el punto.",
                    )
                ],
            },
        ],
    }


def _derivative_document(unit: CourseUnit) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "pedagogicalBlock",
                "attrs": {
                    "nodeId": _id(unit, "definition"),
                    "kind": "definition",
                    "title": "Derivada en un punto",
                },
                "content": [
                    {
                        "type": "displayMath",
                        "attrs": {
                            "nodeId": _id(unit, "derivative"),
                            "latex": r"f'(a)=\lim_{h\to0}\frac{f(a+h)-f(a)}{h}",
                            "label": "derivative-definition",
                        },
                    },
                    _paragraph(
                        unit,
                        "explanation",
                        "La expresión mide la tasa de cambio instantánea cuando el límite existe.",
                    ),
                ],
            },
            {
                "type": "pedagogicalBlock",
                "attrs": {
                    "nodeId": _id(unit, "warning"),
                    "kind": "warning",
                    "title": "Existencia",
                },
                "content": [
                    _paragraph(
                        unit,
                        "warning-p",
                        "La derivada no existe en el punto si este límite no existe o no es finito.",
                    )
                ],
            },
        ],
    }


DOCUMENT_BUILDERS = {
    "Funciones, dominio y rango": _functions_document,
    "Idea intuitiva de límite": _limit_document,
    "Definición de derivada": _derivative_document,
}


class Command(BaseCommand):
    help = "Crea contenido académico demo idempotente sólo en desarrollo."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("El contenido demo sólo se permite con DEBUG=True.")
        self._bootstrap()

    @transaction.atomic
    def _bootstrap(self) -> None:
        organization = Organization.objects.filter(slug="organizacion-demo").first()
        actor = User.objects.filter(email="owner@demo.local").first()
        course = (
            Course.objects.filter(organization=organization, slug=DEMO_COURSE_SLUG)
            .prefetch_related("revisions__modules__units")
            .first()
            if organization
            else None
        )
        if not organization or not actor or not course:
            raise CommandError(
                "Ejecuta primero los bootstrap demo de organización, currículo y cursos."
            )
        revision = course.revisions.order_by("-number").first()
        if (
            revision is None
            or revision.authoring_status not in EDITABLE_AUTHORING_STATUSES
        ):
            raise CommandError(
                "El curso demo existente no tiene una revisión editable; no se modificó."
            )
        units = CourseUnit.objects.filter(
            module__revision=revision,
            module__status=StructureStatus.ACTIVE,
            status=StructureStatus.ACTIVE,
        ).select_related("module__revision")
        created = 0
        unchanged = 0
        for unit in units:
            builder = DOCUMENT_BUILDERS.get(unit.title, _fallback_document)
            current = (
                UnitContentDocument.objects.filter(unit=unit)
                .select_related("current_version")
                .first()
            )
            expected = (
                current.current_version.number
                if current is not None and current.current_version is not None
                else 0
            )
            result = save_unit_content(
                actor=actor,
                organization=organization,
                revision=revision,
                unit=unit,
                expected_document_version=expected,
                schema_version=1,
                content=builder(unit),
            )
            if result.no_op:
                unchanged += 1
            else:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Contenido demo listo: {created} versiones creadas, "
                f"{unchanged} unidades sin cambios. Curso: {DEMO_COURSE_SLUG}."
            )
        )
