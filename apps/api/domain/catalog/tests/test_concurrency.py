from __future__ import annotations

from threading import Barrier, Thread

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase

from domain.catalog.exceptions import PrerequisiteCycle
from domain.catalog.models import Subject, SubjectPrerequisite, Topic
from domain.catalog.services import (
    create_area,
    create_discipline,
    create_root_topic,
    create_subject,
    replace_subject_prerequisites,
)
from domain.organizations.models import Organization
from domain.organizations.services import create_organization_with_owner


class CatalogConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_two_opposite_prerequisites_finish_with_at_most_one_edge(self) -> None:
        actor = get_user_model().objects.create_user(
            email="owner@example.test", password="Password123!x"
        )
        EmailAddress.objects.create(
            user=actor, email=actor.email, primary=True, verified=True
        )
        organization = create_organization_with_owner(
            actor=actor, name="Institución", slug="institucion"
        )
        area = create_area(
            actor=actor,
            organization=organization,
            name="Área",
            slug="area",
            description="",
        )
        discipline = create_discipline(
            actor=actor,
            organization=organization,
            area=area,
            name="Disciplina",
            slug="disciplina",
            description="",
        )
        first = create_subject(
            actor=actor,
            organization=organization,
            discipline=discipline,
            name="Primera",
            slug="primera",
            description="",
        )
        second = create_subject(
            actor=actor,
            organization=organization,
            discipline=discipline,
            name="Segunda",
            slug="segunda",
            description="",
        )
        barrier = Barrier(2)
        outcomes: list[str] = []

        def replace(target_id, prerequisite_id) -> None:
            close_old_connections()
            try:
                local_actor = get_user_model().objects.get(pk=actor.pk)
                local_organization = Organization.objects.get(pk=organization.pk)
                target = Subject.objects.select_related("discipline__area").get(
                    pk=target_id
                )
                prerequisite = Subject.objects.select_related("discipline__area").get(
                    pk=prerequisite_id
                )
                barrier.wait(timeout=10)
                replace_subject_prerequisites(
                    actor=local_actor,
                    organization=local_organization,
                    target=target,
                    prerequisites=[(prerequisite, "required", "")],
                )
                outcomes.append("created")
            except PrerequisiteCycle:
                outcomes.append("cycle")
            finally:
                close_old_connections()

        workers = [
            Thread(target=replace, args=(first.pk, second.pk)),
            Thread(target=replace, args=(second.pk, first.pk)),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=15)
            self.assertFalse(worker.is_alive())
        self.assertCountEqual(outcomes, ["created", "cycle"])
        self.assertEqual(SubjectPrerequisite.objects.count(), 1)

    def test_concurrent_topic_writes_keep_the_materialized_path_consistent(
        self,
    ) -> None:
        actor = get_user_model().objects.create_user(
            email="tree-owner@example.test", password="Password123!x"
        )
        EmailAddress.objects.create(
            user=actor, email=actor.email, primary=True, verified=True
        )
        organization = create_organization_with_owner(
            actor=actor, name="Institución árbol", slug="institucion-arbol"
        )
        area = create_area(
            actor=actor,
            organization=organization,
            name="Área",
            slug="area",
            description="",
        )
        discipline = create_discipline(
            actor=actor,
            organization=organization,
            area=area,
            name="Disciplina",
            slug="disciplina",
            description="",
        )
        subject = create_subject(
            actor=actor,
            organization=organization,
            discipline=discipline,
            name="Asignatura",
            slug="asignatura",
            description="",
        )
        barrier = Barrier(2)
        outcomes: list[str] = []

        def create_topic(title: str, slug: str) -> None:
            close_old_connections()
            try:
                local_actor = get_user_model().objects.get(pk=actor.pk)
                local_organization = Organization.objects.get(pk=organization.pk)
                local_subject = Subject.objects.select_related("discipline__area").get(
                    pk=subject.pk
                )
                barrier.wait(timeout=10)
                create_root_topic(
                    actor=local_actor,
                    organization=local_organization,
                    subject=local_subject,
                    title=title,
                    slug=slug,
                    description="",
                )
                outcomes.append("created")
            finally:
                close_old_connections()

        workers = [
            Thread(target=create_topic, args=("Primer tema", "primer-tema")),
            Thread(target=create_topic, args=("Segundo tema", "segundo-tema")),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=15)
            self.assertFalse(worker.is_alive())

        self.assertEqual(outcomes, ["created", "created"])
        self.assertEqual(Topic.objects.filter(subject=subject).count(), 2)
        self.assertFalse(any(Topic.objects.find_problems()))
