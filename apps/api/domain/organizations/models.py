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

from .choices import MembershipEventType, MembershipStatus, RoleCode

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
    membership: models.ForeignKey[Membership, Membership] = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="events"
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
        return f"{self.membership}:{self.event_type}"
