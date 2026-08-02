import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from domain.learning.choices import AcademicGroupLevel, AcademicGroupRole
from domain.learning.exceptions import LearningPermissionDenied
from domain.learning.services import (
    create_academic_group,
    replace_academic_group_roster,
)
from domain.organizations.models import Membership
from domain.organizations.services import create_organization_with_owner


class AcademicGroupTests(TestCase):
    def test_group_reuses_memberships_without_granting_course_access(self) -> None:
        owner = get_user_model().objects.create_user(
            email="group-owner@example.test", password="OwnerPassword!42"
        )
        organization = create_organization_with_owner(
            actor=owner, name="Colegio", slug="colegio"
        )
        learner = get_user_model().objects.create_user(
            email="group-learner@example.test", password="LearnerPassword!42"
        )
        membership = Membership.objects.create(
            organization=organization,
            user=learner,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        group = create_academic_group(
            actor=owner,
            organization=organization,
            name="Undécimo A",
            academic_year=2026,
            level=AcademicGroupLevel.SECONDARY_11,
            section="A",
        )

        replace_academic_group_roster(
            actor=owner,
            group=group,
            members=[
                {"membership_id": membership.id, "role": AcademicGroupRole.LEARNER}
            ],
            expected_group_version=group.lock_version,
        )

        row = group.roster.get()
        self.assertEqual(row.membership, membership)
        self.assertEqual(row.role, AcademicGroupRole.LEARNER)
        self.assertFalse(membership.course_enrollments.exists())

        with self.assertRaises(LearningPermissionDenied):
            replace_academic_group_roster(
                actor=owner,
                group=group,
                members=[
                    {
                        "membership_id": uuid.uuid4(),
                        "role": AcademicGroupRole.INSTRUCTOR,
                    }
                ],
                expected_group_version=group.lock_version + 1,
            )
        row.refresh_from_db()
        self.assertEqual(row.status, "active")
        self.assertEqual(row.role, AcademicGroupRole.LEARNER)

        replace_academic_group_roster(
            actor=owner,
            group=group,
            members=[],
            expected_group_version=group.lock_version + 1,
        )
        row.refresh_from_db()
        self.assertEqual(row.status, "inactive")
        self.assertIsNotNone(row.ended_at)
