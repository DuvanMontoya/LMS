from __future__ import annotations

from copy import deepcopy

from domain.courses.services import (
    create_module,
    create_unit,
    replace_unit_learning_objectives,
)
from domain.courses.tests.support import CourseFixtureMixin


class ContentFixtureMixin(CourseFixtureMixin):
    def unit_context(self, *, lesson_kind: str = "document"):
        owner, organization, subject, objective, topic, revision = (
            self.course_revision()
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Funciones",
        )
        unit, revision = create_unit(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=revision.lock_version,
            title="Dominio y rango",
            lesson_kind=lesson_kind,
        )
        revision = replace_unit_learning_objectives(
            actor=owner,
            organization=organization,
            unit=unit,
            expected_version=revision.lock_version,
            learning_objectives=[objective],
        )
        return owner, organization, revision, module, unit, objective, topic


def full_document() -> dict[str, object]:
    return deepcopy(
        {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {
                        "nodeId": "10000000-0000-4000-8000-000000000001",
                        "level": 2,
                    },
                    "content": [{"type": "text", "text": "Funciones"}],
                },
                {
                    "type": "paragraph",
                    "attrs": {"nodeId": "10000000-0000-4000-8000-000000000002"},
                    "content": [
                        {"type": "text", "text": "La función "},
                        {
                            "type": "inlineMath",
                            "attrs": {
                                "nodeId": "10000000-0000-4000-8000-000000000003",
                                "latex": "f(x)=x^2",
                            },
                        },
                        {
                            "type": "text",
                            "text": " tiene dominio real.",
                            "marks": [{"type": "bold"}],
                        },
                    ],
                },
                {
                    "type": "pedagogicalBlock",
                    "attrs": {
                        "nodeId": "10000000-0000-4000-8000-000000000004",
                        "kind": "definition",
                        "title": "Definición",
                    },
                    "content": [
                        {
                            "type": "paragraph",
                            "attrs": {"nodeId": "10000000-0000-4000-8000-000000000005"},
                            "content": [
                                {
                                    "type": "text",
                                    "text": "El dominio contiene las entradas admitidas.",
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "displayMath",
                    "attrs": {
                        "nodeId": "10000000-0000-4000-8000-000000000006",
                        "latex": "f(x)=x^2",
                        "label": "eq-funcion",
                    },
                },
                {
                    "type": "codeBlock",
                    "attrs": {
                        "nodeId": "10000000-0000-4000-8000-000000000007",
                        "language": "python",
                        "caption": "Implementación",
                        "code": "def f(x: float) -> float:\n    return x**2",
                    },
                },
                {
                    "type": "table",
                    "attrs": {
                        "nodeId": "10000000-0000-4000-8000-000000000008",
                        "caption": "Valores de la función",
                    },
                    "content": [
                        {
                            "type": "tableRow",
                            "attrs": {"nodeId": "10000000-0000-4000-8000-000000000009"},
                            "content": [
                                {
                                    "type": "tableHeader",
                                    "attrs": {
                                        "nodeId": "10000000-0000-4000-8000-000000000010",
                                        "colspan": 1,
                                        "rowspan": 1,
                                        "colwidth": None,
                                    },
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "attrs": {
                                                "nodeId": "10000000-0000-4000-8000-000000000011"
                                            },
                                            "content": [{"type": "text", "text": "x"}],
                                        }
                                    ],
                                },
                                {
                                    "type": "tableHeader",
                                    "attrs": {
                                        "nodeId": "10000000-0000-4000-8000-000000000012",
                                        "colspan": 1,
                                        "rowspan": 1,
                                        "colwidth": None,
                                    },
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "attrs": {
                                                "nodeId": "10000000-0000-4000-8000-000000000013"
                                            },
                                            "content": [
                                                {"type": "text", "text": "f(x)"}
                                            ],
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "tableRow",
                            "attrs": {"nodeId": "10000000-0000-4000-8000-000000000014"},
                            "content": [
                                {
                                    "type": "tableCell",
                                    "attrs": {
                                        "nodeId": "10000000-0000-4000-8000-000000000015",
                                        "colspan": 1,
                                        "rowspan": 1,
                                        "colwidth": None,
                                    },
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "attrs": {
                                                "nodeId": "10000000-0000-4000-8000-000000000016"
                                            },
                                            "content": [{"type": "text", "text": "2"}],
                                        }
                                    ],
                                },
                                {
                                    "type": "tableCell",
                                    "attrs": {
                                        "nodeId": "10000000-0000-4000-8000-000000000017",
                                        "colspan": 1,
                                        "rowspan": 1,
                                        "colwidth": None,
                                    },
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "attrs": {
                                                "nodeId": "10000000-0000-4000-8000-000000000018"
                                            },
                                            "content": [{"type": "text", "text": "4"}],
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )


def empty_document() -> dict[str, object]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"nodeId": "20000000-0000-4000-8000-000000000001"},
            }
        ],
    }
