# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportUnusedExpression=false
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from domain.catalog.models import (
    AcademicArea,
    Concept,
    Discipline,
    LearningObjective,
    Subject,
    SubjectTeachingResponsibility,
    Topic,
)
from domain.catalog.services import (
    assign_subject_teaching_responsibility,
    close_subject_teaching_responsibility,
    create_area,
    create_concept,
    create_discipline,
    create_learning_objective,
    create_root_topic,
    create_subject,
    replace_concept_prerequisites,
    replace_subject_prerequisites,
)
from domain.identity.models import User
from domain.organizations.models import Membership, Organization


class Command(BaseCommand):
    help = "Crea un currículo de demostración idempotente sólo para desarrollo local."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("El currículo demo sólo se permite con DEBUG=True.")
        organization = Organization.objects.filter(slug="organizacion-demo").first()
        actor = User.objects.filter(email="author@demo.local").first()
        if not organization or not actor:
            raise CommandError("Ejecuta primero bootstrap_demo_organizations.")
        responsibility_manager = User.objects.filter(
            email="administrator@demo.local"
        ).first()
        if not responsibility_manager:
            raise CommandError("La organización demo no contiene sus roles académicos.")
        area = AcademicArea.objects.filter(
            organization=organization, slug="matematicas"
        ).first() or create_area(
            actor=actor,
            organization=organization,
            name="Matemáticas",
            slug="matematicas",
            description="Estructura académica de demostración.",
        )
        fundamentals = Discipline.objects.filter(
            area=area, slug="fundamentos-matematicos"
        ).first() or create_discipline(
            actor=actor,
            organization=organization,
            area=area,
            name="Fundamentos matemáticos",
            slug="fundamentos-matematicos",
            description="",
        )
        calculus = Discipline.objects.filter(
            area=area, slug="calculo-y-analisis"
        ).first() or create_discipline(
            actor=actor,
            organization=organization,
            area=area,
            name="Cálculo y análisis",
            slug="calculo-y-analisis",
            description="",
        )
        precalculus = Subject.objects.filter(
            discipline=fundamentals, slug="precalculo"
        ).first() or create_subject(
            actor=actor,
            organization=organization,
            discipline=fundamentals,
            name="Precálculo",
            slug="precalculo",
            description="",
        )
        differential = Subject.objects.filter(
            discipline=calculus, slug="calculo-diferencial"
        ).first() or create_subject(
            actor=actor,
            organization=organization,
            discipline=calculus,
            name="Cálculo diferencial",
            slug="calculo-diferencial",
            description="",
        )
        author_membership = Membership.objects.get(
            organization=organization, user=actor, status="active"
        )
        today = timezone.localdate()
        for subject in (precalculus, differential):
            responsibility = SubjectTeachingResponsibility.objects.filter(
                subject=subject,
                membership=author_membership,
                ended_at__isnull=True,
            ).first()
            if responsibility and not (
                responsibility.starts_on <= today
                and (responsibility.ends_on is None or responsibility.ends_on >= today)
            ):
                close_subject_teaching_responsibility(
                    actor=responsibility_manager,
                    responsibility=responsibility,
                    ended_on=(
                        responsibility.ends_on
                        if responsibility.ends_on and responsibility.ends_on < today
                        else max(today, responsibility.starts_on)
                    ),
                )
                responsibility = None
            if responsibility is None:
                assign_subject_teaching_responsibility(
                    actor=responsibility_manager,
                    organization=organization,
                    subject=subject,
                    membership=author_membership,
                    starts_on=today,
                    ends_on=None,
                    rationale="Responsabilidad académica de la autoría demo local.",
                )
        Topic.objects.filter(
            subject=precalculus, slug="funciones"
        ).first() or create_root_topic(
            actor=actor,
            organization=organization,
            subject=precalculus,
            title="Funciones",
            slug="funciones",
            description="",
        )
        for title, slug in (
            ("Límites", "limites"),
            ("Continuidad", "continuidad"),
            ("Derivadas", "derivadas"),
        ):
            if not Topic.objects.filter(subject=differential, slug=slug).exists():
                create_root_topic(
                    actor=actor,
                    organization=organization,
                    subject=differential,
                    title=title,
                    slug=slug,
                    description="",
                )
        concepts = {}
        for name, slug, definition in (
            ("Función", "funcion", "Relación entre variables."),
            ("Dominio", "dominio", "Valores de entrada admitidos."),
            ("Rango", "rango", "Valores de salida posibles."),
            ("Límite", "limite", "Valor al que se aproxima una función."),
            ("Continuidad", "continuidad", "Propiedad local de una función."),
            ("Derivada", "derivada", "Razón de cambio local."),
        ):
            concepts[slug] = Concept.objects.filter(
                organization=organization, slug=slug
            ).first() or create_concept(
                actor=actor,
                organization=organization,
                name=name,
                slug=slug,
                definition=definition,
            )
        for code, statement in (
            ("OBJ-001", "Interpretar funciones y sus representaciones."),
            ("OBJ-002", "Analizar límites de funciones."),
            ("OBJ-003", "Aplicar la derivada para estudiar variación."),
        ):
            if not LearningObjective.objects.filter(
                subject=differential, code=code
            ).exists():
                create_learning_objective(
                    actor=actor,
                    organization=organization,
                    subject=differential,
                    code=code,
                    statement=statement,
                    description="",
                    cognitive_level="",
                )
        replace_subject_prerequisites(
            actor=actor,
            organization=organization,
            target=differential,
            prerequisites=[
                (precalculus, "required", "Base para el cálculo diferencial.")
            ],
        )
        replace_concept_prerequisites(
            actor=actor,
            organization=organization,
            target=concepts["derivada"],
            prerequisites=[
                (concepts["funcion"], "required", ""),
                (concepts["limite"], "required", ""),
            ],
        )
        replace_concept_prerequisites(
            actor=actor,
            organization=organization,
            target=concepts["continuidad"],
            prerequisites=[(concepts["limite"], "required", "")],
        )
        self.stdout.write("Currículo demo creado o actualizado.")
