from __future__ import annotations

from argparse import ArgumentParser
from typing import TYPE_CHECKING, cast

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.organizations.exceptions import OrganizationDomainError
from domain.organizations.services import create_organization_with_owner

if TYPE_CHECKING:
    from domain.identity.models import User


class Command(BaseCommand):
    help = "Crea una organización con un propietario existente y verificado."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--name", required=True)
        parser.add_argument("--slug", required=True)
        parser.add_argument("--owner-email", required=True)

    def handle(self, *args: object, **options: object) -> str:
        email = str(options["owner_email"])
        owner = cast(
            "User | None",
            get_user_model().objects.filter(email__iexact=email).first(),
        )
        if owner is None:
            raise CommandError("No existe una cuenta con ese correo.")
        if not owner.is_active:
            raise CommandError("La cuenta propietaria debe estar activa.")
        try:
            organization = create_organization_with_owner(
                actor=owner,
                name=str(options["name"]),
                slug=str(options["slug"]),
            )
        except OrganizationDomainError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(f"Organización creada: {organization.slug}")
        )
        return organization.slug
