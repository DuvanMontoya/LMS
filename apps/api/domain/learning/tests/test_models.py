from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from domain.learning.models import LearningEvent
from domain.learning.services import create_cohort, enroll_member
from domain.organizations.models import Membership

from .support import LearningFixtureMixin


class LearningModelTests(LearningFixtureMixin, TestCase):
    def test_learning_event_is_protected_by_model_and_postgresql(self) -> None:
        *_, enrollment = self.learning_context()
        event = LearningEvent.objects.filter(enrollment=enrollment).first()
        assert event is not None
        event.event_type = "course_started"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE learning_learningevent SET event_type = %s WHERE id = %s",
                    ["course_started", event.id],
                )
        with self.assertRaises(DatabaseError), transaction.atomic():
            LearningEvent.objects.filter(pk=event.pk).delete()

    def test_enrolled_cohort_release_change_is_rejected_by_postgresql(self) -> None:
        (
            owner,
            _learner,
            organization,
            _membership,
            revision,
            _module,
            _unit,
            publication,
            release,
            _enrollment,
        ) = self.learning_context()
        second = self.second_release(
            owner=owner,
            organization=organization,
            revision=revision,
            publication=publication,
            release=release,
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            name="Cohorte inmutable",
        )
        student = get_user_model().objects.create_user(
            email="cohort-trigger@example.test", password="StrongLearningPassword!42"
        )
        membership = Membership.objects.create(
            organization=organization,
            user=student,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        enroll_member(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=membership,
            cohort=cohort,
        )
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE learning_learningcohort SET release_id = %s WHERE id = %s",
                    [second.id, cohort.id],
                )
