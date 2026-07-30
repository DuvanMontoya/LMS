from __future__ import annotations

import os
from argparse import ArgumentParser
from typing import TYPE_CHECKING, cast

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import (
    Membership,
    MembershipRoleAssignment,
    Organization,
)
from domain.organizations.services import (
    add_existing_member_with_roles,
    assign_role,
    create_organization_with_owner,
    reactivate_membership,
    revoke_membership,
)

if TYPE_CHECKING:
    from domain.identity.managers import UserManager
    from domain.identity.models import User


class Command(BaseCommand):
    help = (
        "Crea o actualiza un acceso personal sólo en desarrollo local. "
        "La contraseña se lee de LMS_LOCAL_ACCESS_PASSWORD."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--organization-slug", required=True)
        parser.add_argument(
            "--organization-name",
            help=(
                "Nombre para crear la organización cuando el slug todavía no existe."
            ),
        )
        parser.add_argument(
            "--exclusive",
            action="store_true",
            help=(
                "Revoca las demás membresías locales de esta identidad para "
                "mantener un único contexto de acceso."
            ),
        )
        parser.add_argument(
            "--role",
            choices=[role.value for role in RoleCode],
            default=RoleCode.ADMINISTRATOR.value,
        )

    def handle(self, *args: object, **options: object) -> str:
        if not settings.DEBUG:
            raise CommandError("El acceso local sólo se permite con DEBUG=True.")

        password = os.environ.get("LMS_LOCAL_ACCESS_PASSWORD")
        if not password:
            raise CommandError("LMS_LOCAL_ACCESS_PASSWORD es obligatorio.")

        email = str(options["email"]).strip().lower()
        organization_slug = str(options["organization_slug"])
        organization_name = str(options.get("organization_name") or "").strip()
        exclusive = bool(options.get("exclusive"))
        role = RoleCode(str(options["role"]))
        effective_role = role

        with transaction.atomic():
            user = self._upsert_user(email=email, password=password)
            organization = Organization.objects.filter(slug=organization_slug).first()
            if organization is None:
                if not organization_name:
                    raise CommandError(
                        "La organización local no existe; indica "
                        "--organization-name para crearla."
                    )
                organization = create_organization_with_owner(
                    actor=user,
                    name=organization_name,
                    slug=organization_slug,
                )
                effective_role = RoleCode.OWNER
            else:
                owner_membership = (
                    Membership.objects.select_related("user")
                    .filter(
                        organization=organization,
                        status=MembershipStatus.ACTIVE.value,
                        role_assignments__role=RoleCode.OWNER.value,
                        role_assignments__revoked_at__isnull=True,
                    )
                    .first()
                )
                if owner_membership is None:
                    raise CommandError(
                        "La organización local no tiene un propietario activo."
                    )

                membership = (
                    Membership.objects.filter(
                        organization=organization,
                        user=user,
                    )
                    .exclude(status=MembershipStatus.REVOKED.value)
                    .first()
                )
                if membership is None:
                    add_existing_member_with_roles(
                        actor=owner_membership.user,
                        organization=organization,
                        user=user,
                        roles={role},
                    )
                else:
                    if membership.status == MembershipStatus.SUSPENDED.value:
                        membership = reactivate_membership(
                            actor=owner_membership.user,
                            membership=membership,
                        )
                    has_role = MembershipRoleAssignment.objects.filter(
                        membership=membership,
                        role=role.value,
                        revoked_at__isnull=True,
                    ).exists()
                    if not has_role:
                        assign_role(
                            actor=owner_membership.user,
                            membership=membership,
                            role=role,
                        )

            if exclusive:
                self._revoke_other_memberships(
                    organization=organization,
                    user=user,
                )

        message = (
            f"Acceso local listo para {email} en {organization.slug} "
            f"con rol {effective_role.value}."
        )
        self.stdout.write(self.style.SUCCESS(message))
        return message

    @staticmethod
    def _revoke_other_memberships(
        *,
        organization: Organization,
        user: User,
    ) -> None:
        other_memberships = (
            Membership.objects.select_related("organization")
            .filter(
                user=user,
                status__in=[
                    MembershipStatus.ACTIVE.value,
                    MembershipStatus.SUSPENDED.value,
                ],
            )
            .exclude(organization=organization)
        )
        for membership in other_memberships:
            owner_membership = (
                Membership.objects.select_related("user")
                .filter(
                    organization=membership.organization,
                    status=MembershipStatus.ACTIVE.value,
                    role_assignments__role=RoleCode.OWNER.value,
                    role_assignments__revoked_at__isnull=True,
                )
                .first()
            )
            if owner_membership is None:
                raise CommandError(
                    "No se pudo cerrar una membresía previa porque su "
                    "organización no tiene propietario activo."
                )
            revoke_membership(
                actor=owner_membership.user,
                membership=membership,
            )

    @staticmethod
    def _upsert_user(*, email: str, password: str) -> User:
        manager = cast("UserManager", get_user_model().objects)
        user = manager.filter(email__iexact=email).first()
        if user is None:
            user = manager.create_user(email=email, password=password)
        else:
            update_fields: list[str] = []
            if not user.check_password(password):
                user.set_password(password)
                update_fields.append("password")
            if not user.is_active:
                user.is_active = True
                update_fields.append("is_active")
            if update_fields:
                user.save(update_fields=update_fields)
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": True},
        )
        return user
