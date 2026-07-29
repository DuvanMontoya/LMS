from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from domain.courses.choices import AuthoringStatus
from domain.courses.exceptions import CourseSlugReserved
from domain.courses.models import CourseRevision, CourseRevisionTransition
from domain.courses.services import create_course

from .support import CourseFixtureMixin


class CourseModelTests(CourseFixtureMixin, TestCase):
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
