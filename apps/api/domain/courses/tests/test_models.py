from __future__ import annotations

import uuid
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from domain.courses.choices import AuthoringStatus
from domain.courses.exceptions import CourseSlugReserved
from domain.courses.models import CourseRevision, CourseRevisionTransition
from domain.courses.services import create_course

from .support import CourseFixtureMixin


class CourseModelTests(CourseFixtureMixin, TestCase):
    @override_settings(DEBUG=False)
    def test_demo_bootstrap_rejects_non_development_settings(self) -> None:
        with self.assertRaisesMessage(
            CommandError, "Los cursos demo sólo se permiten con DEBUG=True."
        ):
            call_command("bootstrap_demo_courses", stdout=StringIO())

    def test_uuid_slug_rules_and_physical_delete_protection(self) -> None:
        owner, organization, subject, _, _ = self.curriculum()
        with self.assertRaises(CourseSlugReserved):
            create_course(
                actor=owner,
                organization=organization,
                slug="admin",
                title="Reservado",
                summary="No se crea.",
                primary_subject=subject,
            )
        revision = create_course(
            actor=owner,
            organization=organization,
            slug="curso",
            title="Curso",
            summary="Resumen",
            primary_subject=subject,
        )
        self.assertIsInstance(revision.course_id, uuid.UUID)
        self.assertIsInstance(revision.id, uuid.UUID)
        with self.assertRaises(ValidationError):
            revision.course.delete()
        revision.course.slug = "otro-slug"
        with self.assertRaises(ValidationError):
            revision.course.full_clean()

    def test_case_insensitive_slug_and_only_one_open_revision(self) -> None:
        owner, organization, subject, _, _ = self.curriculum()
        first = create_course(
            actor=owner,
            organization=organization,
            slug="curso",
            title="Curso",
            summary="Resumen",
            primary_subject=subject,
        )
        with self.assertRaises(CourseSlugReserved):
            create_course(
                actor=owner,
                organization=organization,
                slug="CURSO",
                title="Duplicado",
                summary="Resumen",
                primary_subject=subject,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            CourseRevision.objects.create(
                course=first.course,
                number=2,
                based_on_revision=None,
                title="Otra",
                summary="Otra revisión",
                authoring_status=AuthoringStatus.DRAFT,
                status_changed_by=owner,
                created_by=owner,
                updated_by=owner,
            )

    def test_transition_history_is_append_only(self) -> None:
        *_, revision = self.course_revision()
        transition = CourseRevisionTransition.objects.get(revision=revision)
        transition.note = "Mutación indebida"
        with self.assertRaises(ValidationError):
            transition.save()
        with self.assertRaises(ValidationError):
            transition.delete()
