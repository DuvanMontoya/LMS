from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.test import TransactionTestCase

from domain.courses.models import Course, CourseRevision
from domain.identity.models import User
from domain.organizations.models import Organization
from domain.publishing.exceptions import PublicationConflict
from domain.publishing.models import CoursePublication, CourseRelease
from domain.publishing.services import (
    publish_approved_revision,
    withdraw_publication,
)

from .support import PublishingFixtureMixin


class PublicationConcurrencyTests(PublishingFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def test_two_publishers_create_one_release_and_one_current_pointer(self) -> None:
        owner, organization, revision, *_ = self.approved_revision_context()
        barrier = threading.Barrier(2)

        def publish() -> str:
            close_old_connections()
            try:
                actor = User.objects.get(pk=owner.pk)
                scoped_organization = Organization.objects.get(pk=organization.pk)
                scoped_revision = CourseRevision.objects.select_related("course").get(
                    pk=revision.pk
                )
                barrier.wait(timeout=10)
                publish_approved_revision(
                    actor=actor,
                    organization=scoped_organization,
                    course=scoped_revision.course,
                    revision=scoped_revision,
                    expected_publication_version=0,
                )
                return "published"
            except PublicationConflict:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = sorted(executor.map(lambda _index: publish(), range(2)))

        self.assertEqual(outcomes, ["conflict", "published"])
        self.assertEqual(
            CourseRelease.objects.filter(course=revision.course).count(), 1
        )
        publication = CoursePublication.objects.get(course=revision.course)
        self.assertEqual(publication.current_release.number, 1)
        self.assertEqual(
            Course.objects.get(pk=revision.course_id).releases.count(),
            1,
        )

    def test_publish_same_revision_racing_with_withdraw_cannot_reactivate(self) -> None:
        owner, organization, revision, *_, publication, _release = (
            self.published_context()
        )
        barrier = threading.Barrier(2)

        def publish() -> str:
            close_old_connections()
            try:
                actor = User.objects.get(pk=owner.pk)
                scoped_organization = Organization.objects.get(pk=organization.pk)
                scoped_revision = CourseRevision.objects.select_related("course").get(
                    pk=revision.pk
                )
                barrier.wait(timeout=10)
                publish_approved_revision(
                    actor=actor,
                    organization=scoped_organization,
                    course=scoped_revision.course,
                    revision=scoped_revision,
                    expected_publication_version=publication.lock_version,
                )
                return "publish_checked"
            except PublicationConflict:
                return "conflict"
            finally:
                close_old_connections()

        def withdraw() -> str:
            close_old_connections()
            try:
                actor = User.objects.get(pk=owner.pk)
                scoped_organization = Organization.objects.get(pk=organization.pk)
                course = Course.objects.get(pk=revision.course_id)
                barrier.wait(timeout=10)
                withdraw_publication(
                    actor=actor,
                    organization=scoped_organization,
                    course=course,
                    expected_publication_version=publication.lock_version,
                    note="Retiro concurrente verificado.",
                )
                return "withdrawn"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            publish_future = executor.submit(publish)
            withdraw_future = executor.submit(withdraw)
            outcomes = sorted((publish_future.result(), withdraw_future.result()))

        self.assertIn(
            outcomes,
            (["publish_checked", "withdrawn"], ["conflict", "withdrawn"]),
        )
        publication.refresh_from_db()
        self.assertEqual(publication.status, "withdrawn")
        self.assertEqual(
            CourseRelease.objects.filter(course=revision.course).count(), 1
        )
