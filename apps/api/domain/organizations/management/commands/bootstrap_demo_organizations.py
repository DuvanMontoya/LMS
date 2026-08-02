from __future__ import annotations

from argparse import ArgumentParser
from typing import TYPE_CHECKING, cast

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import Membership, Organization
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
    replace_membership_roles,
)

if TYPE_CHECKING:
    from domain.identity.managers import UserManager
    from domain.identity.models import User


class Command(BaseCommand):
    help = "Crea cuentas y organizaciones de demostración sólo para desarrollo local."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--password", required=True)

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError(
                "Las cuentas de demostración sólo se permiten con DEBUG=True."
            )
        password = str(options["password"])

        def user(email: str, first_name: str, last_name: str) -> User:
            existing = cast(
                "User | None", get_user_model().objects.filter(email=email).first()
            )
            if existing is None:
                manager = cast("UserManager", get_user_model().objects)
                existing = manager.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
            else:
                existing.set_password(password)
                existing.is_active = True
                existing.first_name = first_name
                existing.last_name = last_name
                existing.save(
                    update_fields=[
                        "password",
                        "is_active",
                        "first_name",
                        "last_name",
                    ]
                )
            EmailAddress.objects.update_or_create(
                user=existing,
                email=email,
                defaults={"primary": True, "verified": True},
            )
            return existing

        owner = user("owner@demo.local", "Propietario", "Demo")
        administrator = user("administrator@demo.local", "Administrador", "Demo")
        learner = user("learner@demo.local", "Estudiante", "Demo")
        author = user("author@demo.local", "Autor", "Demo")
        reviewer = user("reviewer@demo.local", "Revisor", "Demo")
        instructor = user("instructor@demo.local", "Docente", "Demo")
        external_owner = user("external@demo.local", "Propietario", "Externo")

        organization = Organization.objects.filter(slug="organizacion-demo").first()
        if organization is None:
            organization = create_organization_with_owner(
                actor=owner,
                name="Organización de demostración",
                slug="organizacion-demo",
            )
        if not Membership.objects.filter(
            organization=organization,
            user=owner,
            status=MembershipStatus.ACTIVE.value,
        ).exists():
            raise CommandError(
                "La organización demo existente no tiene su owner activo."
            )
        for member, roles in (
            (administrator, {RoleCode.ADMINISTRATOR}),
            (learner, {RoleCode.LEARNER}),
            (author, {RoleCode.AUTHOR}),
            (reviewer, {RoleCode.REVIEWER}),
            (instructor, {RoleCode.INSTRUCTOR}),
        ):
            membership = Membership.objects.filter(
                organization=organization,
                user=member,
                status=MembershipStatus.ACTIVE.value,
            ).first()
            if membership is None:
                add_existing_member_with_roles(
                    actor=owner, organization=organization, user=member, roles=roles
                )
            else:
                replace_membership_roles(
                    actor=owner, membership=membership, roles=roles
                )
        if not Organization.objects.filter(slug="organizacion-externa-demo").exists():
            create_organization_with_owner(
                actor=external_owner,
                name="Organización externa de demostración",
                slug="organizacion-externa-demo",
            )
        self.stdout.write("Cuentas y organizaciones demo creadas o actualizadas.")
