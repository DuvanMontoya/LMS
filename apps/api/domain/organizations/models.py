from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower, Trim
from django.utils import timezone

from .choices import (
    InvitationStatus,
    InvitationType,
    JoinRequestStatus,
    MembershipEventType,
    MembershipStatus,
    RoleCode,
)

# New Django relations retain runtime validation; django-stubs cannot infer them
# until all generated reverse accessors have declarations.
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

if TYPE_CHECKING:
    from domain.identity.models import User


RESERVED_ORGANIZATION_SLUGS = frozenset(
    {
        "admin",
        "api",
        "auth",
        "health",
        "accounts",
        "_allauth",
        "estudiar",
        "organizaciones",
        "static",
        "media",
    }
)


class Organization(models.Model):
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    name: models.CharField[str, str] = models.CharField(max_length=160)
    slug: models.SlugField[str, str] = models.SlugField(max_length=80, unique=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True
    )
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(name=Trim(F("name"))) & ~Q(name=""),
                name="organizations_name_trimmed_nonempty",
            ),
            models.CheckConstraint(
                condition=Q(slug=Lower(F("slug"))),
                name="organizations_slug_lowercase",
            ),
        ]
        indexes = [models.Index(fields=["slug"], name="org_slug_ix")]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        if self.slug in RESERVED_ORGANIZATION_SLUGS:
            raise ValidationError({"slug": "Este slug está reservado."})
        if not self._state.adding:
            original_slug = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if original_slug is not None and original_slug != self.slug:
                raise ValidationError({"slug": "El slug institucional es inmutable."})


class OrganizationMembershipSettings(models.Model):  # noqa: DJ012
    """Mutable organization policy, isolated from historical memberships."""

    organization: models.OneToOneField[Organization, Organization] = (
        models.OneToOneField(
            Organization, on_delete=models.PROTECT, related_name="membership_settings"
        )
    )
    public_join_enabled = models.BooleanField(default=False)
    join_requires_approval = models.BooleanField(default=True)
    allowed_email_domains = models.JSONField(default=list, blank=True)
    default_role = models.CharField(
        max_length=32, choices=RoleCode.choices, default=RoleCode.LEARNER
    )
    invitation_expiry_hours = models.PositiveIntegerField(default=168)
    allow_admin_managed_accounts = models.BooleanField(default=True)
    allow_bulk_invitations = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_membership_settings_updates",
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)
    lock_version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(invitation_expiry_hours__gte=1)
                & Q(invitation_expiry_hours__lte=720),
                name="organizations_invitation_expiry_bounded",
            ),
            models.CheckConstraint(
                condition=~Q(default_role=RoleCode.OWNER),
                name="organizations_default_role_not_owner",
            ),
        ]

    def __str__(self) -> str:
        return f"settings:{self.organization.slug}"

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.allowed_email_domains, list):
            raise ValidationError({"allowed_email_domains": "Debe ser una lista."})
        domains: list[str] = []
        for raw_domain in self.allowed_email_domains:
            if not isinstance(raw_domain, str):
                raise ValidationError({"allowed_email_domains": "Dominio inválido."})
            domain = raw_domain.strip().lower()
            if (
                not domain
                or "*" in domain
                or "@" in domain
                or domain.startswith(".")
                or domain.endswith(".")
                or any(char.isspace() for char in domain)
            ):
                raise ValidationError({"allowed_email_domains": "Dominio inválido."})
            domains.append(domain)
        if len(set(domains)) != len(domains):
            raise ValidationError({"allowed_email_domains": "No repitas dominios."})
        self.allowed_email_domains = sorted(domains)


class MembershipInvitation(models.Model):  # noqa: DJ012
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="membership_invitations"
    )
    email = models.EmailField()
    existing_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="membership_invitations",
    )
    invited_roles = models.JSONField(default=list)
    invitation_type = models.CharField(max_length=24, choices=InvitationType.choices)
    status = models.CharField(
        max_length=16,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
    )
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="membership_invitations_created",
    )
    given_name = models.CharField(max_length=150, blank=True)
    family_name = models.CharField(max_length=150, blank=True)
    preferred_name = models.CharField(max_length=150, blank=True)
    member_type = models.CharField(max_length=80, blank=True)
    institutional_id = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    locale = models.CharField(max_length=16, default="es")
    timezone_name = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "status", "expires_at"],
                name="org_invite_due_ix",
            ),
            models.Index(fields=["organization", "email"], name="org_invite_email_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                condition=Q(status=InvitationStatus.PENDING),
                name="organizations_one_pending_invitation_email",
            ),
            models.CheckConstraint(
                condition=Q(accepted_at__isnull=True)
                | Q(status=InvitationStatus.ACCEPTED),
                name="organizations_invitation_acceptance_state",
            ),
            models.CheckConstraint(
                condition=Q(revoked_at__isnull=True)
                | Q(status=InvitationStatus.REVOKED),
                name="organizations_invitation_revocation_state",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.email}:{self.status}"

    def clean(self) -> None:
        super().clean()
        self.email = self.email.strip().lower()
        if not isinstance(self.invited_roles, list) or not self.invited_roles:
            raise ValidationError({"invited_roles": "Debes indicar al menos un rol."})
        try:
            roles = {RoleCode(role) for role in self.invited_roles}
        except ValueError as error:
            raise ValidationError({"invited_roles": "Rol inválido."}) from error
        if RoleCode.OWNER in roles:
            raise ValidationError({"invited_roles": "Owner no puede ser invitado."})
        self.invited_roles = sorted(role.value for role in roles)


class OrganizationJoinRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="join_requests"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_join_requests",
    )
    email = models.EmailField()
    status = models.CharField(
        max_length=16,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="organization_join_requests_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"], name="org_join_status_ix")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                condition=Q(status=JoinRequestStatus.PENDING),
                name="organizations_one_pending_join_request",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.email}:{self.status}"


class OrganizationMemberProfile(models.Model):
    membership = models.OneToOneField(
        "Membership", on_delete=models.PROTECT, related_name="institutional_profile"
    )
    member_type = models.CharField(max_length=80, blank=True)
    institutional_id = models.CharField(max_length=120, blank=True)
    preferred_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    locale = models.CharField(max_length=16, default="es")
    timezone = models.CharField(max_length=64, default="UTC")
    administrative_notes = models.TextField(max_length=4000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"profile:{self.membership_id}"


class Membership(models.Model):
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization: models.ForeignKey[Organization, Organization] = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="memberships"
    )
    user: models.ForeignKey[User, User] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_memberships",
    )
    status: models.CharField[str, str] = models.CharField(
        max_length=16, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE
    )
    joined_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        default=timezone.now, editable=False
    )
    status_changed_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        default=timezone.now
    )
    status_changed_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_membership_status_changes",
        null=True,
        blank=True,
    )
    suspended_at: models.DateTimeField[datetime | None, datetime | None] = (
        models.DateTimeField(null=True, blank=True)
    )
    revoked_at: models.DateTimeField[datetime | None, datetime | None] = (
        models.DateTimeField(null=True, blank=True)
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                condition=~Q(status=MembershipStatus.REVOKED.value),
                name="organizations_one_current_membership",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=MembershipStatus.ACTIVE.value,
                        suspended_at__isnull=True,
                        revoked_at__isnull=True,
                    )
                    | Q(
                        status=MembershipStatus.SUSPENDED.value,
                        suspended_at__isnull=False,
                        revoked_at__isnull=True,
                    )
                    | Q(status=MembershipStatus.REVOKED.value, revoked_at__isnull=False)
                ),
                name="organizations_membership_state_timestamps",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="org_member_state_ix"),
            models.Index(fields=["user", "status"], name="org_member_user_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.user.email}"


class MembershipRoleAssignment(models.Model):
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    membership: models.ForeignKey[Membership, Membership] = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="role_assignments"
    )
    role: models.CharField[str, str] = models.CharField(
        max_length=32, choices=RoleCode.choices
    )
    assigned_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        default=timezone.now, editable=False
    )
    assigned_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_roles_assigned",
        null=True,
        blank=True,
    )
    revoked_at: models.DateTimeField[datetime | None, datetime | None] = (
        models.DateTimeField(null=True, blank=True)
    )
    revoked_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_roles_revoked",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "role"],
                condition=Q(revoked_at__isnull=True),
                name="organizations_one_active_role_assignment",
            ),
            models.CheckConstraint(
                condition=Q(revoked_at__isnull=True)
                | Q(revoked_at__gte=F("assigned_at")),
                name="organizations_role_revoked_after_assigned",
            ),
        ]
        indexes = [
            models.Index(fields=["membership", "role"], name="org_role_member_role_ix")
        ]

    def __str__(self) -> str:
        return f"{self.membership}:{self.role}"


class MembershipEvent(models.Model):
    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization: models.ForeignKey[Organization, Organization] = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="membership_events"
    )
    membership: models.ForeignKey[Membership | None, Membership | None] = (
        models.ForeignKey(
            Membership,
            on_delete=models.PROTECT,
            related_name="events",
            null=True,
            blank=True,
        )
    )
    actor: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_membership_events",
        null=True,
        blank=True,
    )
    event_type: models.CharField[str, str] = models.CharField(
        max_length=32, choices=MembershipEventType.choices
    )
    role: models.CharField[str, str] = models.CharField(
        max_length=32, choices=RoleCode.choices, blank=True, default=""
    )
    previous_status: models.CharField[str, str] = models.CharField(
        max_length=16, choices=MembershipStatus.choices, blank=True, default=""
    )
    new_status: models.CharField[str, str] = models.CharField(
        max_length=16, choices=MembershipStatus.choices, blank=True, default=""
    )
    details = models.JSONField(default=dict, blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        default=timezone.now, editable=False
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "created_at"], name="org_event_org_created_ix"
            ),
            models.Index(
                fields=["membership", "created_at"], name="org_event_member_created_ix"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.event_type}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("MembershipEvent es append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("MembershipEvent es append-only.")
