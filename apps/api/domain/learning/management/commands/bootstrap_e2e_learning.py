# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.identity.models import User
from domain.organizations.models import Organization
from domain.publishing.models import CoursePublication
from domain.publishing.services import publish_approved_revision

COURSE_SLUG = "publicacion-inmutable-e2e"


class Command(BaseCommand):
    help = "Publica la fuente efímera requerida por el E2E aislado de learning."

    def handle(self, *args: object, **options: object) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError("Este comando sólo puede ejecutarse con settings E2E.")
        self._bootstrap()

    @transaction.atomic
    def _bootstrap(self) -> None:
        organization = Organization.objects.get(slug="organizacion-a")
        owner = User.objects.get(email="owner@organizations.e2e.test")
        course = organization.courses.get(slug=COURSE_SLUG)
        revision = course.revisions.get(number=1)
        publication = CoursePublication.objects.filter(course=course).first()
        if publication is None:
            publish_approved_revision(
                actor=owner,
                organization=organization,
                course=course,
                revision=revision,
                expected_publication_version=0,
            )
        self.stdout.write("Release E2E de aprendizaje disponible; sin matrículas.")
