# pyright: reportUnknownArgumentType=false, reportMissingParameterType=false
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.catalog.models import LearningObjective, Subject, Topic
from domain.courses.models import Course
from domain.courses.services import (
    create_course,
    create_module,
    create_unit,
    replace_unit_learning_objectives,
    replace_unit_topics,
)
from domain.identity.models import User
from domain.organizations.models import Organization


class Command(BaseCommand):
    help = "Crea el curso demo idempotente sólo para desarrollo local."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError("Los cursos demo sólo se permiten con DEBUG=True.")
        organization = Organization.objects.filter(slug="organizacion-demo").first()
        actor = User.objects.filter(email="owner@demo.local").first()
        if not organization or not actor:
            raise CommandError("Ejecuta primero bootstrap_demo_organizations.")
        if Course.objects.filter(
            organization=organization, slug="introduccion-calculo-diferencial"
        ).exists():
            self.stdout.write("Curso demo ya existente; se conservaron sus IDs.")
            return

        differential = Subject.objects.filter(
            discipline__area__organization=organization,
            slug="calculo-diferencial",
        ).first()
        precalculus = Subject.objects.filter(
            discipline__area__organization=organization, slug="precalculo"
        ).first()
        if not differential or not precalculus:
            raise CommandError("Ejecuta primero bootstrap_demo_curriculum.")
        objectives = list(
            LearningObjective.objects.filter(subject=differential).order_by("code")
        )
        topics = {
            topic.slug: topic
            for topic in Topic.objects.filter(
                subject__in=[differential, precalculus]
            ).order_by("slug")
        }
        if (
            len(objectives) < 3
            or not {
                "funciones",
                "limites",
                "continuidad",
                "derivadas",
            }
            <= topics.keys()
        ):
            raise CommandError(
                "El currículo demo no contiene las referencias esperadas."
            )

        revision = create_course(
            actor=actor,
            organization=organization,
            slug="introduccion-calculo-diferencial",
            title="Introducción al cálculo diferencial",
            summary="Estructura breve para recorrer el flujo de autoría.",
            primary_subject=differential,
            supporting_subjects=[precalculus],
            learning_objectives=objectives,
            estimated_duration_minutes=480,
        )
        plan = (
            (
                "Fundamentos de funciones",
                (
                    ("Funciones, dominio y rango", "funciones", objectives[0]),
                    ("Representaciones de una función", "funciones", objectives[0]),
                ),
            ),
            (
                "Límites y continuidad",
                (
                    ("Idea intuitiva de límite", "limites", objectives[1]),
                    ("Límites laterales", "limites", objectives[1]),
                    ("Continuidad", "continuidad", objectives[1]),
                ),
            ),
            (
                "Introducción a la derivada",
                (
                    ("Razón de cambio", "derivadas", objectives[2]),
                    ("Definición de derivada", "derivadas", objectives[2]),
                    ("Interpretación geométrica", "derivadas", objectives[2]),
                ),
            ),
        )
        for module_title, units in plan:
            module, revision = create_module(
                actor=actor,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title=module_title,
            )
            for unit_title, topic_slug, objective in units:
                unit, revision = create_unit(
                    actor=actor,
                    organization=organization,
                    module=module,
                    expected_version=revision.lock_version,
                    title=unit_title,
                )
                revision = replace_unit_topics(
                    actor=actor,
                    organization=organization,
                    unit=unit,
                    expected_version=revision.lock_version,
                    topics=[topics[topic_slug]],
                )
                revision = replace_unit_learning_objectives(
                    actor=actor,
                    organization=organization,
                    unit=unit,
                    expected_version=revision.lock_version,
                    learning_objectives=[objective],
                )
        self.stdout.write(
            "Curso demo creado en borrador; no se aprobó ni publicó automáticamente."
        )
