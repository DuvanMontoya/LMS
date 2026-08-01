from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.catalog.services import (
    create_area,
    create_discipline,
    create_learning_objective,
    create_root_topic,
    create_subject,
)
from domain.organizations.choices import RoleCode
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)

if TYPE_CHECKING:
    from domain.identity.managers import UserManager
    from domain.identity.models import User


class Command(BaseCommand):
    help = "Crea fixtures institucionales efímeros exclusivamente para Playwright."

    def handle(self, *args: object, **options: object) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError("Este comando sólo puede ejecutarse con settings E2E.")
        password = os.environ.get("E2E_ORGANIZATIONS_PASSWORD")
        if not password:
            raise CommandError("E2E_ORGANIZATIONS_PASSWORD es obligatorio.")

        def user(email: str) -> User:
            existing = cast(
                "User | None", get_user_model().objects.filter(email=email).first()
            )
            if existing is not None:
                return existing
            manager = cast("UserManager", get_user_model().objects)
            created = manager.create_user(email=email, password=password)
            EmailAddress.objects.create(
                user=created, email=email, primary=True, verified=True
            )
            return created

        def superuser(email: str) -> User:
            existing = cast(
                "User | None", get_user_model().objects.filter(email=email).first()
            )
            if existing is not None:
                return existing
            manager = cast("UserManager", get_user_model().objects)
            created = manager.create_superuser(email=email, password=password)
            EmailAddress.objects.create(
                user=created, email=email, primary=True, verified=True
            )
            return created

        owner = user("owner@organizations.e2e.test")
        administrator = user("administrator@organizations.e2e.test")
        author = user("author@organizations.e2e.test")
        instructor = user("instructor@organizations.e2e.test")
        learner = user("learner@organizations.e2e.test")
        reviewer = user("reviewer@organizations.e2e.test")
        external_owner = user("external@organizations.e2e.test")
        superuser("platform-admin@organizations.e2e.test")
        user("candidate@organizations.e2e.test")
        user("rejoin@organizations.e2e.test")

        organization = create_organization_with_owner(
            actor=owner, name="Organización A", slug="organizacion-a"
        )
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=administrator,
            roles={RoleCode.ADMINISTRATOR},
        )
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=author,
            roles={RoleCode.AUTHOR},
        )
        area = create_area(
            actor=owner,
            organization=organization,
            name="Matemáticas",
            slug="matematicas",
            description="",
        )
        discipline = create_discipline(
            actor=owner,
            organization=organization,
            area=area,
            name="Fundamentos",
            slug="fundamentos",
            description="",
        )
        subject = create_subject(
            actor=owner,
            organization=organization,
            discipline=discipline,
            name="Precálculo",
            slug="precalculo",
            description="",
        )
        create_root_topic(
            actor=owner,
            organization=organization,
            subject=subject,
            title="Funciones",
            slug="funciones",
            description="",
        )
        create_learning_objective(
            actor=owner,
            organization=organization,
            subject=subject,
            code="OBJ-COURSE-001",
            statement="Interpretar funciones mediante distintas representaciones.",
            description="",
            cognitive_level="understand",
        )
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=instructor,
            roles={RoleCode.INSTRUCTOR},
        )
        add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=reviewer,
            roles={RoleCode.REVIEWER},
        )
        create_organization_with_owner(
            actor=external_owner, name="Organización B", slug="organizacion-b"
        )
        self.stdout.write("E2E institutional fixtures created.")
