# pyright: reportUnknownMemberType=false
from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError

from domain.courses.models import Course
from domain.publishing.integrity import verify_release_chain


class Command(BaseCommand):
    help = "Verifica schema, digests, índices y encadenamiento de releases."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--organization", dest="organization_slug")
        parser.add_argument("--course", dest="course_slug")

    def handle(self, *args: object, **options: object) -> None:
        courses = Course.objects.filter(releases__isnull=False).distinct()
        organization_slug = options.get("organization_slug")
        course_slug = options.get("course_slug")
        if organization_slug:
            courses = courses.filter(organization__slug=organization_slug)
        if course_slug:
            courses = courses.filter(slug=course_slug)

        checked = 0
        failures: list[str] = []
        for course in courses.select_related("organization").order_by(
            "organization__slug", "slug"
        ):
            result = verify_release_chain(course)
            checked += 1
            label = f"{course.organization.slug}/{course.slug}"
            if result.valid:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK {label}: {result.checked_releases} release(s)."
                    )
                )
                continue
            for issue in result.issues:
                release = (
                    f" release {issue.release_number}"
                    if issue.release_number is not None
                    else ""
                )
                failures.append(f"{label}{release}: {issue.code}: {issue.detail}")

        if failures:
            raise CommandError(
                "La verificación de releases falló:\n" + "\n".join(failures)
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Integridad verificada: {checked} curso(s), sin alteraciones."
            )
        )
