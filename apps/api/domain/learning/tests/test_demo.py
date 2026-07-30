from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from domain.learning.models import CourseEnrollment, LearningCohort
from domain.organizations.models import Membership
from domain.publishing.tests.support import PublishingFixtureMixin


class LearningDemoTests(PublishingFixtureMixin, TestCase):
    @override_settings(DEBUG=False)
    def test_demo_rejects_non_development_settings(self) -> None:
        with self.assertRaises(CommandError):
            call_command("bootstrap_demo_learning", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_demo_is_idempotent_and_preserves_the_release_assignment(self) -> None:
        (
            owner,
            organization,
            revision,
            _module,
            _unit,
            _objective,
            _topic,
            _publication,
            release,
        ) = self.published_context()
        organization.slug = "organizacion-demo"
        organization.save(update_fields=["slug"])
        revision.course.slug = "introduccion-calculo-diferencial"
        revision.course.save(update_fields=["slug"])
        owner.email = "owner@demo.local"
        owner.save(update_fields=["email"])
        learner = get_user_model().objects.create_user(
            email="learner@demo.local", password="StrongLearningPassword!42"
        )
        Membership.objects.create(
            organization=organization,
            user=learner,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        call_command("bootstrap_demo_learning", stdout=StringIO())
        enrollment = CourseEnrollment.objects.get(membership__user=learner)
        original_assignment = enrollment.current_release_assignment_id
        call_command("bootstrap_demo_learning", stdout=StringIO())
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.current_release_assignment_id, original_assignment)
        self.assertEqual(enrollment.current_release_assignment.release_id, release.id)
        self.assertEqual(LearningCohort.objects.count(), 1)
        self.assertEqual(
            CourseEnrollment.objects.filter(membership__user=learner).count(), 1
        )
