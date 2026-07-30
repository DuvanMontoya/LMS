# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.catalog.models import LearningObjective, Subject, Topic
from domain.content.services import save_unit_content
from domain.courses.models import Course
from domain.courses.services import (
    approve_revision,
    create_course,
    create_module,
    create_unit,
    replace_unit_learning_objectives,
    replace_unit_topics,
    submit_revision_for_review,
)
from domain.identity.models import User
from domain.organizations.models import Organization

COURSE_SLUG = "publicacion-inmutable-e2e"


class Command(BaseCommand):
    help = "Crea una revisión aprobada efímera para E2E de publicación."

    def handle(self, *args: object, **options: object) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError("Este comando sólo puede ejecutarse con settings E2E.")
        self._bootstrap()

    @transaction.atomic
    def _bootstrap(self) -> None:
        organization = Organization.objects.get(slug="organizacion-a")
        owner = User.objects.get(email="owner@organizations.e2e.test")
        if Course.objects.filter(organization=organization, slug=COURSE_SLUG).exists():
            self.stdout.write("Fuente E2E de publicación ya existente.")
            return
        subject = Subject.objects.get(
            discipline__area__organization=organization, slug="precalculo"
        )
        objective = LearningObjective.objects.get(
            subject=subject, code="OBJ-COURSE-001"
        )
        topic = Topic.objects.get(subject=subject, slug="funciones")
        revision = create_course(
            actor=owner,
            organization=organization,
            slug=COURSE_SLUG,
            title="Funciones para lectura institucional",
            summary="Curso verificable para el canal de publicación inmutable.",
            description=(
                "Dos unidades académicas capturadas en un release para lectura "
                "institucional autenticada."
            ),
            primary_subject=subject,
            learning_objectives=[objective],
            estimated_duration_minutes=90,
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Fundamentos de funciones",
        )
        for index, title in enumerate(("Concepto de función", "Dominio y rango"), 1):
            unit, revision = create_unit(
                actor=owner,
                organization=organization,
                module=module,
                expected_version=revision.lock_version,
                title=title,
                summary=f"Unidad {index} del recorrido publicado.",
            )
            revision = replace_unit_topics(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                topics=[topic],
            )
            revision = replace_unit_learning_objectives(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                learning_objectives=[objective],
            )
            save_unit_content(
                actor=owner,
                organization=organization,
                revision=revision,
                unit=unit,
                expected_document_version=0,
                schema_version=1,
                content={
                    "type": "doc",
                    "content": [
                        {
                            "type": "heading",
                            "attrs": {
                                "nodeId": str(
                                    uuid.uuid5(
                                        uuid.NAMESPACE_URL, f"{COURSE_SLUG}:{index}:h"
                                    )
                                ),
                                "level": 2,
                            },
                            "content": [{"type": "text", "text": title}],
                        },
                        {
                            "type": "paragraph",
                            "attrs": {
                                "nodeId": str(
                                    uuid.uuid5(
                                        uuid.NAMESPACE_URL, f"{COURSE_SLUG}:{index}:p"
                                    )
                                )
                            },
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Una función asigna a cada entrada admitida "
                                        "una única salida."
                                    ),
                                }
                            ],
                        },
                    ],
                },
            )
        revision = submit_revision_for_review(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        approve_revision(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            note="Fuente aprobada para E2E.",
        )
        self.stdout.write("Fuente E2E de publicación aprobada y sin publicar.")
