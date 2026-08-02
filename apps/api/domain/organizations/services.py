from __future__ import annotations

import hashlib
import secrets
from datetime import date, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from .capabilities import Capability
from .choices import (
    InvitationStatus,
    InvitationType,
    JoinRequestStatus,
    MembershipEventType,
    MembershipStatus,
    OrganizationStatus,
    RoleCode,
    normalize_member_type,
)
from .exceptions import (
    InitialOwnerUnavailable,
    InvalidMembershipTransition,
    InvitationAlreadyExists,
    InvitationUnavailable,
    JoinRequestAlreadyExists,
    JoinRequestUnavailable,
    LastOwnerViolation,
    ManagedAccountsDisabled,
    MemberAlreadyExists,
    MembershipNotActive,
    OrganizationAccessDenied,
    RevisionConflict,
    RoleAlreadyAssigned,
    RoleAssignmentDenied,
    RoleNotAssigned,
    VerifiedUserRequired,
)
from .models import (
    Membership,
    MembershipEvent,
    MembershipInvitation,
    MembershipRoleAssignment,
    Organization,
    OrganizationJoinRequest,
    OrganizationMemberProfile,
    OrganizationMembershipSettings,
)
from .policies import (
    active_roles,
    can_assign_role,
    can_manage_membership,
    has_capability,
    is_active_platform_operator,
    target_is_active_owner,
)

# ORM related fields are dynamic at this service boundary; policy checks remain
# the authority for every mutation.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

if TYPE_CHECKING:
    from domain.identity.models import User


def _record_event(
    *,
    organization: Organization,
    membership: Membership | None,
    actor: User | None,
    event_type: MembershipEventType,
    role: RoleCode | None = None,
    previous_status: MembershipStatus | None = None,
    new_status: MembershipStatus | None = None,
    details: dict[str, object] | None = None,
) -> MembershipEvent:
    return MembershipEvent.objects.create(
        organization=organization,
        membership=membership,
        actor=actor,
        event_type=event_type,
        role=role.value if role else "",
        previous_status=previous_status.value if previous_status else "",
        new_status=new_status.value if new_status else "",
        details=details or {},
    )


def _locked_organization(organization: Organization) -> Organization:
    return Organization.objects.select_for_update().get(pk=organization.pk)


def _locked_membership(membership: Membership) -> Membership:
    return (
        Membership.objects.select_for_update()
        .select_related("organization", "user")
        .get(pk=membership.pk)
    )


def _active_owner_count(organization: Organization) -> int:
    return MembershipRoleAssignment.objects.filter(
        membership__organization=organization,
        membership__status=MembershipStatus.ACTIVE.value,
        role=RoleCode.OWNER.value,
        revoked_at__isnull=True,
    ).count()


def _ensure_not_last_owner(membership: Membership) -> None:
    if (
        target_is_active_owner(membership)
        and _active_owner_count(membership.organization) <= 1
    ):
        raise LastOwnerViolation(
            "La organización debe conservar un propietario activo."
        )


def _require_capability(
    actor: User | None, organization: Organization, capability: Capability
) -> None:
    if not has_capability(actor, organization, capability):
        raise OrganizationAccessDenied("No tienes capacidad para esta operación.")


@transaction.atomic
def create_organization_with_owner(
    *, actor: User, name: str, slug: str, created_by: User | None = None
) -> Organization:
    audit_actor = created_by or actor
    organization = Organization(name=name, slug=slug)
    organization.full_clean()
    organization.save()
    OrganizationMembershipSettings.objects.create(
        organization=organization, updated_by=audit_actor
    )
    membership = Membership.objects.create(
        organization=organization,
        user=actor,
        status_changed_by=audit_actor,
    )
    # Every membership owns its institutional profile from creation.  Keeping
    # this invariant in the command path means profile reads remain read-only.
    OrganizationMemberProfile.objects.create(membership=membership)
    MembershipRoleAssignment.objects.create(
        membership=membership, role=RoleCode.OWNER.value, assigned_by=audit_actor
    )
    _record_event(
        organization=organization,
        membership=membership,
        actor=audit_actor,
        event_type=MembershipEventType.CREATED,
        new_status=MembershipStatus.ACTIVE,
    )
    _record_event(
        organization=organization,
        membership=membership,
        actor=audit_actor,
        event_type=MembershipEventType.ROLE_ASSIGNED,
        role=RoleCode.OWNER,
    )
    return organization


@transaction.atomic
def provision_platform_organization(
    *,
    actor: User,
    name: str,
    owner_email: str,
    administrator_emails: tuple[str, ...] = (),
) -> Organization:
    """Provision an institution from the platform control plane.

    The public identifier is generated server-side so an operator never has to
    invent or coordinate an institutional code. The designated owner receives
    a one-time invitation; the platform operator does not inherit membership.
    The transaction uses a short random suffix and retries the vanishingly rare
    uniqueness collision.
    """

    if not is_active_platform_operator(actor):
        raise OrganizationAccessDenied("Solo el superadministrador crea instituciones.")

    normalized_owner_email = owner_email.strip().lower()
    normalized_administrators = tuple(
        dict.fromkeys(email.strip().lower() for email in administrator_emails)
    )
    if (
        not normalized_owner_email
        or normalized_owner_email == actor.email.strip().lower()
        or actor.email.strip().lower() in normalized_administrators
        or normalized_owner_email in normalized_administrators
    ):
        raise InitialOwnerUnavailable(
            "El operador no puede ser miembro y las invitaciones no se repiten."
        )

    normalized_name = name.strip()
    base = slugify(normalized_name)[:72].strip("-") or "institucion"
    for _ in range(5):
        generated_slug = f"{base[:73].rstrip('-')}-{secrets.token_hex(3)}"
        try:
            with transaction.atomic():
                organization = Organization(
                    name=normalized_name,
                    slug=generated_slug,
                    status=OrganizationStatus.PENDING_ACTIVATION,
                    activated_at=None,
                )
                organization.full_clean()
                organization.save()
                membership_settings = OrganizationMembershipSettings.objects.create(
                    organization=organization, updated_by=actor
                )
                owner_user = (
                    get_user_model()
                    .objects.filter(email__iexact=normalized_owner_email)
                    .first()
                )
                _create_platform_bootstrap_invitation(
                    actor=actor,
                    organization=organization,
                    membership_settings=membership_settings,
                    email=normalized_owner_email,
                    roles={RoleCode.OWNER},
                    invitation_type=InvitationType.INITIAL_OWNER,
                    existing_user=owner_user,
                )
                for administrator_email in normalized_administrators:
                    existing_user = (
                        get_user_model()
                        .objects.filter(email__iexact=administrator_email)
                        .first()
                    )
                    _create_platform_bootstrap_invitation(
                        actor=actor,
                        organization=organization,
                        membership_settings=membership_settings,
                        email=administrator_email,
                        roles={RoleCode.ADMINISTRATOR},
                        invitation_type=(
                            InvitationType.EXISTING_USER
                            if existing_user is not None
                            else InvitationType.NEW_USER
                        ),
                        existing_user=existing_user,
                    )
                return organization
        except IntegrityError:
            if Organization.objects.filter(slug=generated_slug).exists():
                continue
            raise
    raise OrganizationAccessDenied(
        "No fue posible generar un código institucional único."
    )


def _create_platform_bootstrap_invitation(
    *,
    actor: User,
    organization: Organization,
    membership_settings: OrganizationMembershipSettings,
    email: str,
    roles: set[RoleCode],
    invitation_type: InvitationType,
    existing_user: User | None = None,
) -> MembershipInvitation:
    """Create a control-plane invitation without granting tenant capability."""

    token, digest = _new_invitation_token()
    invitation = MembershipInvitation(
        organization=organization,
        email=email,
        existing_user=existing_user,
        invited_roles=sorted(role.value for role in roles),
        invitation_type=invitation_type,
        token_digest=digest,
        expires_at=timezone.now()
        + timedelta(hours=membership_settings.invitation_expiry_hours),
        invited_by=actor,
    )
    invitation.full_clean()
    invitation.save()
    _record_event(
        organization=organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.INVITATION_CREATED,
        details={"invitation_type": invitation_type.value},
    )
    transaction.on_commit(
        lambda: _send_invitation_email(invitation=invitation, token=token)
    )
    return invitation


@transaction.atomic
def update_organization_name(
    *, actor: User, organization: Organization, name: str
) -> Organization:
    locked = _locked_organization(organization)
    _require_capability(actor, locked, Capability.ORGANIZATION_UPDATE)
    locked.name = name
    locked.full_clean()
    locked.save(update_fields=["name", "updated_at"])
    return locked


@transaction.atomic
def add_existing_member(
    *,
    actor: User,
    organization: Organization,
    user: User,
) -> Membership:
    locked_organization = _locked_organization(organization)
    _require_capability(actor, locked_organization, Capability.MEMBERSHIP_ADD)
    if (
        not user.is_active
        or not EmailAddress.objects.filter(user=user, verified=True).exists()
    ):
        raise VerifiedUserRequired(
            "Solo se pueden agregar usuarios activos con correo verificado."
        )
    if (
        Membership.objects.filter(organization=locked_organization, user=user)
        .exclude(status=MembershipStatus.REVOKED.value)
        .exists()
    ):
        raise MemberAlreadyExists("La persona ya tiene una membresía vigente.")
    membership = Membership.objects.create(
        organization=locked_organization,
        user=user,
        status_changed_by=actor,
    )
    _record_event(
        organization=locked_organization,
        membership=membership,
        actor=actor,
        event_type=MembershipEventType.CREATED,
        new_status=MembershipStatus.ACTIVE,
    )
    OrganizationMemberProfile.objects.get_or_create(membership=membership)
    return membership


@transaction.atomic
def add_existing_member_with_roles(
    *, actor: User, organization: Organization, user: User, roles: set[RoleCode]
) -> Membership:
    membership = add_existing_member(actor=actor, organization=organization, user=user)
    replace_membership_roles(actor=actor, membership=membership, roles=roles)
    return membership


def _transition_membership(
    *,
    actor: User,
    membership: Membership,
    target_status: MembershipStatus,
) -> Membership:
    locked_organization = _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    capability_by_target = {
        MembershipStatus.SUSPENDED: Capability.MEMBERSHIP_SUSPEND,
        MembershipStatus.ACTIVE: Capability.MEMBERSHIP_REACTIVATE,
        MembershipStatus.REVOKED: Capability.MEMBERSHIP_REVOKE,
    }
    capability = capability_by_target[target_status]
    if not can_manage_membership(actor, locked_membership, capability):
        raise OrganizationAccessDenied("No puedes gestionar esta membresía.")
    valid = {
        MembershipStatus.ACTIVE: {MembershipStatus.SUSPENDED, MembershipStatus.REVOKED},
        MembershipStatus.SUSPENDED: {MembershipStatus.ACTIVE, MembershipStatus.REVOKED},
    }
    if target_status not in valid.get(
        MembershipStatus(locked_membership.status), set()
    ):
        raise InvalidMembershipTransition("La transición de membresía no es válida.")
    if target_status in {MembershipStatus.SUSPENDED, MembershipStatus.REVOKED}:
        _ensure_not_last_owner(locked_membership)
    previous_status = MembershipStatus(locked_membership.status)
    now = timezone.now()
    locked_membership.status = target_status.value
    locked_membership.status_changed_at = now
    locked_membership.status_changed_by = actor
    locked_membership.suspended_at = (
        now if target_status == MembershipStatus.SUSPENDED else None
    )
    if target_status == MembershipStatus.REVOKED:
        locked_membership.revoked_at = now
    locked_membership.save(
        update_fields=[
            "status",
            "status_changed_at",
            "status_changed_by",
            "suspended_at",
            "revoked_at",
        ]
    )
    event_type = {
        MembershipStatus.SUSPENDED: MembershipEventType.SUSPENDED,
        MembershipStatus.ACTIVE: MembershipEventType.REACTIVATED,
        MembershipStatus.REVOKED: MembershipEventType.REVOKED,
    }[target_status]
    _record_event(
        organization=locked_organization,
        membership=locked_membership,
        actor=actor,
        event_type=event_type,
        previous_status=previous_status,
        new_status=target_status,
    )
    if target_status == MembershipStatus.REVOKED:
        for assignment in MembershipRoleAssignment.objects.select_for_update().filter(
            membership=locked_membership, revoked_at__isnull=True
        ):
            assignment.revoked_at = now
            assignment.revoked_by = actor
            assignment.save(update_fields=["revoked_at", "revoked_by"])
            _record_event(
                organization=locked_organization,
                membership=locked_membership,
                actor=actor,
                event_type=MembershipEventType.ROLE_REVOKED,
                role=RoleCode(assignment.role),
            )
    return locked_membership


@transaction.atomic
def suspend_membership(*, actor: User, membership: Membership) -> Membership:
    return _transition_membership(
        actor=actor, membership=membership, target_status=MembershipStatus.SUSPENDED
    )


@transaction.atomic
def reactivate_membership(*, actor: User, membership: Membership) -> Membership:
    return _transition_membership(
        actor=actor, membership=membership, target_status=MembershipStatus.ACTIVE
    )


@transaction.atomic
def revoke_membership(*, actor: User, membership: Membership) -> Membership:
    return _transition_membership(
        actor=actor, membership=membership, target_status=MembershipStatus.REVOKED
    )


@transaction.atomic
def assign_role(
    *, actor: User, membership: Membership, role: RoleCode
) -> MembershipRoleAssignment:
    _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    if locked_membership.status == MembershipStatus.REVOKED.value:
        raise MembershipNotActive("No se asignan roles a membresías revocadas.")
    if not can_assign_role(actor, locked_membership, role):
        raise RoleAssignmentDenied("No puedes asignar este rol.")
    current_roles = active_roles(locked_membership)
    _validate_role_combination(current_roles | {role})
    if MembershipRoleAssignment.objects.filter(
        membership=locked_membership, role=role.value, revoked_at__isnull=True
    ).exists():
        raise RoleAlreadyAssigned("El rol ya está asignado.")
    try:
        assignment = MembershipRoleAssignment.objects.create(
            membership=locked_membership, role=role.value, assigned_by=actor
        )
    except IntegrityError as error:
        raise RoleAlreadyAssigned("El rol ya está asignado.") from error
    _record_event(
        organization=locked_membership.organization,
        membership=locked_membership,
        actor=actor,
        event_type=MembershipEventType.ROLE_ASSIGNED,
        role=role,
    )
    return assignment


@transaction.atomic
def replace_membership_roles(
    *, actor: User, membership: Membership, roles: set[RoleCode]
) -> Membership:
    _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    if locked_membership.status == MembershipStatus.ACTIVE.value and not roles:
        raise RoleAssignmentDenied(
            "Una membresía activa debe conservar al menos un rol."
        )
    _validate_role_combination(roles)
    active_assignments = {
        RoleCode(assignment.role): assignment
        for assignment in MembershipRoleAssignment.objects.select_for_update().filter(
            membership=locked_membership, revoked_at__isnull=True
        )
    }
    for role in sorted(active_assignments.keys() - roles, key=str):
        revoke_role(actor=actor, membership=locked_membership, role=role)
    for role in sorted(roles - active_assignments.keys(), key=str):
        assign_role(actor=actor, membership=locked_membership, role=role)
    return locked_membership


@transaction.atomic
def revoke_role(
    *, actor: User, membership: Membership, role: RoleCode
) -> MembershipRoleAssignment:
    _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    if not can_assign_role(actor, locked_membership, role):
        raise RoleAssignmentDenied("No puedes revocar este rol.")
    assignment = (
        MembershipRoleAssignment.objects.select_for_update()
        .filter(membership=locked_membership, role=role.value, revoked_at__isnull=True)
        .first()
    )
    if assignment is None:
        raise RoleNotAssigned("El rol no está asignado.")
    if role == RoleCode.OWNER:
        _ensure_not_last_owner(locked_membership)
    assignment.revoked_at = timezone.now()
    assignment.revoked_by = actor
    assignment.save(update_fields=["revoked_at", "revoked_by"])
    _record_event(
        organization=locked_membership.organization,
        membership=locked_membership,
        actor=actor,
        event_type=MembershipEventType.ROLE_REVOKED,
        role=role,
    )
    return assignment


def _invitation_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_invitation_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, _invitation_digest(token)


def _locked_membership_settings(
    organization: Organization,
) -> OrganizationMembershipSettings:
    settings, _ = OrganizationMembershipSettings.objects.get_or_create(
        organization=organization
    )
    return OrganizationMembershipSettings.objects.select_for_update().get(
        pk=settings.pk
    )


def _validate_roles(roles: set[RoleCode]) -> set[RoleCode]:
    if not roles or RoleCode.OWNER in roles:
        raise RoleAssignmentDenied("Debes indicar roles institucionales no owner.")
    _validate_role_combination(roles)
    return roles


def _validate_role_combination(roles: set[RoleCode]) -> None:
    if RoleCode.OWNER in roles and roles != {RoleCode.OWNER}:
        raise RoleAssignmentDenied(
            "El rol owner es exclusivamente de gobierno institucional."
        )
    if {RoleCode.AUTHOR, RoleCode.REVIEWER}.issubset(roles):
        raise RoleAssignmentDenied(
            "Autor y revisor son funciones incompatibles para preservar la separación de funciones."
        )


def _create_profile_from_invitation(
    *, membership: Membership, invitation: MembershipInvitation
) -> OrganizationMemberProfile:
    profile, _ = OrganizationMemberProfile.objects.get_or_create(membership=membership)
    copied_fields = {
        "first_name": invitation.given_name,
        "middle_name": invitation.middle_name,
        "first_surname": invitation.family_name,
        "second_surname": invitation.second_family_name,
        "member_type": invitation.member_type,
        "institutional_id": invitation.institutional_id,
        "preferred_name": invitation.preferred_name,
        "phone": invitation.phone,
        "whatsapp": invitation.whatsapp,
        "date_of_birth": invitation.date_of_birth,
        "document_type": invitation.document_type,
        "document_number": invitation.document_number,
        "gender": invitation.gender,
        "education_stage": invitation.education_stage,
        "education_institution": invitation.education_institution,
        "education_level": invitation.education_level,
        "department_code": invitation.department_code,
        "municipality": invitation.municipality,
        "address": invitation.address,
        "socioeconomic_stratum": invitation.socioeconomic_stratum,
        "registration_reason": invitation.registration_reason,
        "registration_reason_detail": invitation.registration_reason_detail,
    }
    for field_name, value in copied_fields.items():
        setattr(profile, field_name, value)
    profile.locale = invitation.locale
    profile.timezone = invitation.timezone_name
    profile.full_clean()
    profile.save(update_fields=(*copied_fields, "locale", "timezone", "updated_at"))
    return profile


def _create_active_membership(
    *,
    organization: Organization,
    user: User,
    actor: User | None,
    roles: set[RoleCode],
    invitation: MembershipInvitation | None = None,
) -> Membership:
    existing = (
        Membership.objects.select_for_update()
        .filter(organization=organization, user=user)
        .exclude(status=MembershipStatus.REVOKED.value)
        .first()
    )
    if existing is not None:
        raise MemberAlreadyExists("La persona ya tiene una membresía vigente.")
    membership = Membership.objects.create(
        organization=organization, user=user, status_changed_by=actor
    )
    for role in sorted(roles, key=lambda item: item.value):
        MembershipRoleAssignment.objects.create(
            membership=membership, role=role.value, assigned_by=actor
        )
    if invitation is not None:
        _create_profile_from_invitation(membership=membership, invitation=invitation)
    else:
        OrganizationMemberProfile.objects.get_or_create(membership=membership)
    _record_event(
        organization=organization,
        membership=membership,
        actor=actor,
        event_type=MembershipEventType.CREATED,
        new_status=MembershipStatus.ACTIVE,
    )
    return membership


def _send_invitation_email(*, invitation: MembershipInvitation, token: str) -> None:
    """Send after commit; token remains only in this closure and mail content."""

    activation_url = f"{settings.FRONTEND_ORIGIN}/invitaciones/activar?token={token}"
    context = {
        "activation_url": activation_url,
        "expiration_hours": int(
            (invitation.expires_at - timezone.now()).total_seconds() // 3600
        ),
        "invitation": invitation,
        "platform_name": "Plataforma Académica",
    }
    message = EmailMultiAlternatives(
        subject=f"Tu invitación a {invitation.organization.name}",
        body=render_to_string("organizations/email/invitation.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.email],
        headers={
            "Message-ID": (
                f"<membership-invitation-{invitation.id}-"
                f"{int(invitation.updated_at.timestamp())}@"
                f"{settings.EMAIL_MESSAGE_ID_DOMAIN}>"
            ),
            "Resend-Idempotency-Key": (
                f"membership-invitation-{invitation.id}-{int(invitation.updated_at.timestamp())}"
            ),
            "Auto-Submitted": "auto-generated",
            "X-Auto-Response-Suppress": "All",
        },
    )
    message.attach_alternative(
        render_to_string("organizations/email/invitation.html", context), "text/html"
    )
    message.send(fail_silently=False)


def _send_member_recovery_email(*, membership: Membership, event_id: str) -> None:
    """Invite the member to start allauth's recovery flow in their own browser."""

    recovery_url = urljoin(
        f"{settings.FRONTEND_ORIGIN.rstrip('/')}/", "auth/recuperar-contrasena"
    )
    profile = getattr(membership, "institutional_profile", None)
    context = {
        "membership": membership,
        "member_name": (
            getattr(profile, "preferred_name", "")
            or getattr(profile, "first_name", "")
            or membership.user.email
        ),
        "organization": membership.organization,
        "platform_name": "Plataforma Académica",
        "recovery_url": recovery_url,
    }
    message = EmailMultiAlternatives(
        subject=f"Recupera tu acceso a {membership.organization.name}",
        body=render_to_string("organizations/email/member_recovery.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[membership.user.email],
        headers={
            "Message-ID": f"<member-recovery-{event_id}@{settings.EMAIL_MESSAGE_ID_DOMAIN}>",
            "Resend-Idempotency-Key": f"member-recovery-{event_id}",
            "Auto-Submitted": "auto-generated",
            "X-Auto-Response-Suppress": "All",
        },
    )
    message.attach_alternative(
        render_to_string("organizations/email/member_recovery.html", context),
        "text/html",
    )
    message.send(fail_silently=False)


@transaction.atomic
def update_membership_settings(
    *,
    actor: User,
    organization: Organization,
    expected_version: int,
    public_join_enabled: bool,
    join_requires_approval: bool,
    allowed_email_domains: list[str],
    default_role: RoleCode,
    invitation_expiry_hours: int,
    allow_admin_managed_accounts: bool,
    allow_bulk_invitations: bool,
) -> OrganizationMembershipSettings:
    locked_organization = _locked_organization(organization)
    _require_capability(
        actor, locked_organization, Capability.MEMBERSHIP_SETTINGS_MANAGE
    )
    settings = _locked_membership_settings(locked_organization)
    if settings.lock_version != expected_version:
        raise RevisionConflict("La configuración cambió antes de guardar.")
    settings.public_join_enabled = public_join_enabled
    settings.join_requires_approval = join_requires_approval
    settings.allowed_email_domains = allowed_email_domains
    settings.default_role = default_role.value
    settings.invitation_expiry_hours = invitation_expiry_hours
    settings.allow_admin_managed_accounts = allow_admin_managed_accounts
    settings.allow_bulk_invitations = allow_bulk_invitations
    settings.updated_by = actor
    settings.lock_version += 1
    settings.full_clean()
    settings.save()
    _record_event(
        organization=locked_organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.SETTINGS_UPDATED,
    )
    return settings


def _assert_invitation_available(invitation: MembershipInvitation) -> None:
    if invitation.status != InvitationStatus.PENDING:
        raise InvitationUnavailable("La invitación no está disponible.")
    if invitation.expires_at <= timezone.now():
        invitation.status = InvitationStatus.EXPIRED
        invitation.save(update_fields=("status", "updated_at"))
        raise InvitationUnavailable("La invitación expiró.")


@transaction.atomic
def expire_due_invitations(*, organization: Organization) -> int:
    """Materialize expired invitations before presenting an administrative list.

    Expiry is an objective state, rather than a state that only changes after a
    recipient opens an old link.  No token, recipient data, or actor is stored
    in this maintenance update.
    """

    return MembershipInvitation.objects.filter(
        organization=organization,
        status=InvitationStatus.PENDING,
        expires_at__lte=timezone.now(),
    ).update(status=InvitationStatus.EXPIRED, updated_at=timezone.now())


@transaction.atomic
def create_invitation(
    *,
    actor: User,
    organization: Organization,
    email: str,
    roles: set[RoleCode],
    invitation_type: InvitationType,
    existing_user: User | None = None,
    given_name: str = "",
    family_name: str = "",
    preferred_name: str = "",
    member_type: str = "",
    institutional_id: str = "",
    phone: str = "",
    locale: str = "es",
    timezone_name: str = "UTC",
    middle_name: str = "",
    second_family_name: str = "",
    whatsapp: str = "",
    date_of_birth: date | None = None,
    document_type: str = "",
    document_number: str = "",
    gender: str = "",
    education_stage: str = "",
    education_institution: str = "",
    education_level: str = "",
    department_code: str = "",
    municipality: str = "",
    address: str = "",
    socioeconomic_stratum: str = "",
    registration_reason: str = "",
    registration_reason_detail: str = "",
) -> tuple[MembershipInvitation, str]:
    locked_organization = _locked_organization(organization)
    _require_capability(actor, locked_organization, Capability.MEMBERSHIP_INVITE)
    settings = _locked_membership_settings(locked_organization)
    if (
        invitation_type == InvitationType.MANAGED_ACCOUNT
        and not settings.allow_admin_managed_accounts
    ):
        raise ManagedAccountsDisabled(
            "La institución no permite cuentas administradas."
        )
    clean_email = email.strip().lower()
    if MembershipInvitation.objects.filter(
        organization=locked_organization,
        email__iexact=clean_email,
        status=InvitationStatus.PENDING,
    ).exists():
        raise InvitationAlreadyExists("Ya existe una invitación pendiente.")
    token, digest = _new_invitation_token()
    invitation = MembershipInvitation(
        organization=locked_organization,
        email=clean_email,
        existing_user=existing_user,
        invited_roles=[role.value for role in _validate_roles(roles)],
        invitation_type=invitation_type,
        token_digest=digest,
        expires_at=timezone.now() + timedelta(hours=settings.invitation_expiry_hours),
        invited_by=actor,
        given_name=given_name.strip(),
        middle_name=middle_name.strip(),
        family_name=family_name.strip(),
        second_family_name=second_family_name.strip(),
        preferred_name=preferred_name.strip(),
        member_type=normalize_member_type(member_type),
        institutional_id=institutional_id.strip(),
        phone=phone.strip(),
        whatsapp=whatsapp.strip(),
        date_of_birth=date_of_birth,
        document_type=document_type,
        document_number=document_number.strip(),
        gender=gender,
        education_stage=education_stage,
        education_institution=education_institution.strip(),
        education_level=education_level,
        department_code=department_code,
        municipality=municipality.strip(),
        address=address.strip(),
        socioeconomic_stratum=socioeconomic_stratum,
        registration_reason=registration_reason,
        registration_reason_detail=registration_reason_detail.strip(),
        locale=locale.strip() or "es",
        timezone_name=timezone_name.strip() or "UTC",
    )
    invitation.full_clean()
    invitation.save()
    _record_event(
        organization=locked_organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.INVITATION_CREATED,
        details={"invitation_type": invitation_type.value},
    )
    transaction.on_commit(
        lambda: _send_invitation_email(invitation=invitation, token=token)
    )
    return invitation, token


def invite_person(
    *,
    actor: User,
    organization: Organization,
    email: str,
    roles: set[RoleCode],
    given_name: str = "",
    family_name: str = "",
    preferred_name: str = "",
    member_type: str = "",
    institutional_id: str = "",
    phone: str = "",
    locale: str = "es",
    timezone_name: str = "UTC",
    middle_name: str = "",
    second_family_name: str = "",
    whatsapp: str = "",
    date_of_birth: date | None = None,
    document_type: str = "",
    document_number: str = "",
    gender: str = "",
    education_stage: str = "",
    education_institution: str = "",
    education_level: str = "",
    department_code: str = "",
    municipality: str = "",
    address: str = "",
    socioeconomic_stratum: str = "",
    registration_reason: str = "",
    registration_reason_detail: str = "",
) -> MembershipInvitation:
    """Create the correct invitation without exposing a token to callers."""

    clean_email = email.strip().lower()
    user = get_user_model().objects.filter(email__iexact=clean_email).first()
    invitation_type = (
        InvitationType.EXISTING_USER if user is not None else InvitationType.NEW_USER
    )
    invitation, _ = create_invitation(
        actor=actor,
        organization=organization,
        email=clean_email,
        roles=roles,
        invitation_type=invitation_type,
        existing_user=user,
        given_name=given_name,
        family_name=family_name,
        preferred_name=preferred_name,
        member_type=member_type,
        institutional_id=institutional_id,
        phone=phone,
        locale=locale,
        timezone_name=timezone_name,
        middle_name=middle_name,
        second_family_name=second_family_name,
        whatsapp=whatsapp,
        date_of_birth=date_of_birth,
        document_type=document_type,
        document_number=document_number,
        gender=gender,
        education_stage=education_stage,
        education_institution=education_institution,
        education_level=education_level,
        department_code=department_code,
        municipality=municipality,
        address=address,
        socioeconomic_stratum=socioeconomic_stratum,
        registration_reason=registration_reason,
        registration_reason_detail=registration_reason_detail,
    )
    return invitation


@transaction.atomic
def create_managed_account(
    *,
    actor: User,
    organization: Organization,
    email: str,
    roles: set[RoleCode],
    given_name: str,
    family_name: str,
    preferred_name: str = "",
    member_type: str = "",
    institutional_id: str = "",
    phone: str = "",
    locale: str = "es",
    timezone_name: str = "America/Bogota",
    middle_name: str = "",
    second_family_name: str = "",
    whatsapp: str = "",
    date_of_birth: date | None = None,
    document_type: str = "",
    document_number: str = "",
    gender: str = "",
    education_stage: str = "",
    education_institution: str = "",
    education_level: str = "",
    department_code: str = "",
    municipality: str = "",
    address: str = "",
    socioeconomic_stratum: str = "",
    registration_reason: str = "",
    registration_reason_detail: str = "",
) -> tuple[MembershipInvitation, str]:
    clean_email = email.strip().lower()
    user_model = get_user_model()
    if user_model.objects.filter(email__iexact=clean_email).exists():
        raise InvitationAlreadyExists("No fue posible crear la invitación.")
    user = user_model(
        email=clean_email,
        first_name=given_name.strip(),
        last_name=" ".join(
            value
            for value in (family_name.strip(), second_family_name.strip())
            if value
        ),
        is_active=False,
    )
    user.set_unusable_password()
    user.save()
    EmailAddress.objects.create(
        user=user, email=clean_email, primary=True, verified=False
    )
    invitation, token = create_invitation(
        actor=actor,
        organization=organization,
        email=clean_email,
        roles=roles,
        invitation_type=InvitationType.MANAGED_ACCOUNT,
        existing_user=user,
        given_name=given_name,
        family_name=family_name,
        preferred_name=preferred_name,
        member_type=member_type,
        institutional_id=institutional_id,
        phone=phone,
        locale=locale,
        timezone_name=timezone_name,
        middle_name=middle_name,
        second_family_name=second_family_name,
        whatsapp=whatsapp,
        date_of_birth=date_of_birth,
        document_type=document_type,
        document_number=document_number,
        gender=gender,
        education_stage=education_stage,
        education_institution=education_institution,
        education_level=education_level,
        department_code=department_code,
        municipality=municipality,
        address=address,
        socioeconomic_stratum=socioeconomic_stratum,
        registration_reason=registration_reason,
        registration_reason_detail=registration_reason_detail,
    )
    _record_event(
        organization=organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.MANAGED_ACCOUNT_CREATED,
    )
    return invitation, token


@transaction.atomic
def resend_invitation(*, actor: User, invitation: MembershipInvitation) -> str:
    locked = (
        MembershipInvitation.objects.select_for_update()
        .select_related("organization")
        .get(pk=invitation.pk)
    )
    _require_capability(
        actor, locked.organization, Capability.MEMBERSHIP_INVITATION_MANAGE
    )
    return _rotate_invitation_token(actor=actor, invitation=locked)


def _rotate_invitation_token(*, actor: User, invitation: MembershipInvitation) -> str:
    locked = invitation
    _assert_invitation_available(locked)
    token, digest = _new_invitation_token()
    locked.token_digest = digest
    locked.expires_at = timezone.now() + timedelta(
        hours=_locked_membership_settings(locked.organization).invitation_expiry_hours
    )
    locked.save(update_fields=("token_digest", "expires_at", "updated_at"))
    _record_event(
        organization=locked.organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.INVITATION_RESENT,
    )
    transaction.on_commit(
        lambda: _send_invitation_email(invitation=locked, token=token)
    )
    return token


@transaction.atomic
def resend_platform_bootstrap_invitation(
    *, actor: User, invitation: MembershipInvitation
) -> str:
    locked = (
        MembershipInvitation.objects.select_for_update()
        .select_related("organization")
        .get(pk=invitation.pk)
    )
    _require_platform_bootstrap_invitation(actor=actor, invitation=locked)
    return _rotate_invitation_token(actor=actor, invitation=locked)


@transaction.atomic
def correct_managed_account_email(
    *, actor: User, invitation: MembershipInvitation, email: str
) -> MembershipInvitation:
    """Correct an inactive managed account before activation.

    The replacement address receives a freshly generated one-time link.  The
    former link becomes unusable, and the administrator never receives either
    token.  This intentionally applies only to institution-managed accounts:
    changing the address of an existing or public account would silently change
    whose identity is being invited.
    """

    locked = (
        MembershipInvitation.objects.select_for_update(of=("self",))
        .select_related("organization", "existing_user")
        .get(pk=invitation.pk)
    )
    _require_capability(
        actor, locked.organization, Capability.MEMBERSHIP_INVITATION_MANAGE
    )
    _assert_invitation_available(locked)
    if (
        locked.invitation_type != InvitationType.MANAGED_ACCOUNT
        or locked.existing_user is None
        or locked.existing_user.is_active
    ):
        raise InvitationUnavailable(
            "Solo se puede corregir una cuenta administrada pendiente."
        )

    clean_email = email.strip().lower()
    user = locked.existing_user
    user_model = get_user_model()
    if (
        user_model.objects.filter(email__iexact=clean_email)
        .exclude(pk=user.pk)
        .exists()
    ):
        raise InvitationAlreadyExists("No fue posible actualizar la invitación.")
    if (
        EmailAddress.objects.filter(email__iexact=clean_email)
        .exclude(user=user)
        .exists()
    ):
        raise InvitationAlreadyExists("No fue posible actualizar la invitación.")
    if (
        MembershipInvitation.objects.filter(
            organization=locked.organization,
            email__iexact=clean_email,
            status=InvitationStatus.PENDING,
        )
        .exclude(pk=locked.pk)
        .exists()
    ):
        raise InvitationAlreadyExists("Ya existe una invitación pendiente.")

    user.email = clean_email
    user.save(update_fields=("email",))
    email_address, _ = EmailAddress.objects.select_for_update().get_or_create(
        user=user,
        defaults={"email": clean_email, "primary": True, "verified": False},
    )
    email_address.email = clean_email
    email_address.primary = True
    email_address.verified = False
    email_address.save(update_fields=("email", "primary", "verified"))

    token, digest = _new_invitation_token()
    locked.email = clean_email
    locked.token_digest = digest
    locked.expires_at = timezone.now() + timedelta(
        hours=_locked_membership_settings(locked.organization).invitation_expiry_hours
    )
    locked.save(update_fields=("email", "token_digest", "expires_at", "updated_at"))
    _record_event(
        organization=locked.organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.INVITATION_UPDATED,
        details={"fields": ["email"]},
    )
    transaction.on_commit(
        lambda: _send_invitation_email(invitation=locked, token=token)
    )
    return locked


@transaction.atomic
def bulk_transition_memberships(
    *,
    actor: User,
    organization: Organization,
    membership_ids: list[str],
    target_status: MembershipStatus,
) -> list[Membership]:
    """Apply one authorized lifecycle action atomically to selected members."""

    locked_organization = _locked_organization(organization)
    unique_ids = set(membership_ids)
    memberships = list(
        Membership.objects.filter(
            organization=locked_organization, id__in=unique_ids
        ).order_by("id")
    )
    if len(memberships) != len(unique_ids):
        raise OrganizationAccessDenied(
            "No puedes gestionar una membresía fuera de contexto."
        )
    updated: list[Membership] = []
    for membership in memberships:
        updated.append(
            _transition_membership(
                actor=actor, membership=membership, target_status=target_status
            )
        )
    return updated


@transaction.atomic
def revoke_invitation(
    *, actor: User, invitation: MembershipInvitation
) -> MembershipInvitation:
    locked = (
        MembershipInvitation.objects.select_for_update()
        .select_related("organization")
        .get(pk=invitation.pk)
    )
    _require_capability(
        actor, locked.organization, Capability.MEMBERSHIP_INVITATION_MANAGE
    )
    return _revoke_locked_invitation(actor=actor, invitation=locked)


def _revoke_locked_invitation(
    *, actor: User, invitation: MembershipInvitation
) -> MembershipInvitation:
    locked = invitation
    _assert_invitation_available(locked)
    locked.status = InvitationStatus.REVOKED
    locked.revoked_at = timezone.now()
    locked.save(update_fields=("status", "revoked_at", "updated_at"))
    _record_event(
        organization=locked.organization,
        membership=None,
        actor=actor,
        event_type=MembershipEventType.INVITATION_REVOKED,
    )
    return locked


def _require_platform_bootstrap_invitation(
    *, actor: User, invitation: MembershipInvitation
) -> None:
    if (
        not is_active_platform_operator(actor)
        or invitation.organization.status != OrganizationStatus.PENDING_ACTIVATION
        or invitation.invitation_type
        not in {
            InvitationType.INITIAL_OWNER,
            InvitationType.EXISTING_USER,
            InvitationType.NEW_USER,
        }
    ):
        raise OrganizationAccessDenied(
            "La invitación no pertenece a un bootstrap institucional pendiente."
        )


@transaction.atomic
def revoke_platform_bootstrap_invitation(
    *, actor: User, invitation: MembershipInvitation
) -> MembershipInvitation:
    locked = (
        MembershipInvitation.objects.select_for_update()
        .select_related("organization")
        .get(pk=invitation.pk)
    )
    _require_platform_bootstrap_invitation(actor=actor, invitation=locked)
    return _revoke_locked_invitation(actor=actor, invitation=locked)


def begin_invitation_activation(
    *, request: HttpRequest, token: str
) -> MembershipInvitation:
    digest = _invitation_digest(token)
    invitation = (
        MembershipInvitation.objects.select_related("organization")
        .filter(token_digest=digest)
        .first()
    )
    if invitation is None:
        raise InvitationUnavailable("La invitación no está disponible.")
    _assert_invitation_available(invitation)
    # A one-time invitation grants the ability to activate or accept an
    # institutional account. Rotate any anonymous session identifier before
    # binding that capability to server-side state.
    request.session.cycle_key()
    request.session["organization_invitation_id"] = str(invitation.id)
    request.session["organization_invitation_digest"] = digest
    request.session.modified = True
    return invitation


def _session_invitation(
    request: HttpRequest, *, require_available: bool = True
) -> MembershipInvitation | None:
    invitation_id = request.session.get("organization_invitation_id")
    digest = request.session.get("organization_invitation_digest")
    if not isinstance(invitation_id, str) or not isinstance(digest, str):
        return None
    invitation = (
        MembershipInvitation.objects.select_related("organization", "existing_user")
        .filter(pk=invitation_id, token_digest=digest)
        .first()
    )
    if invitation is None:
        return None
    if require_available:
        try:
            _assert_invitation_available(invitation)
        except InvitationUnavailable:
            return None
    return invitation


def session_has_valid_signup_invitation(request: HttpRequest) -> bool:
    return session_signup_invitation(request) is not None


def session_signup_invitation(request: HttpRequest) -> MembershipInvitation | None:
    """Return the invitation that authorizes one exact private signup."""

    invitation = _session_invitation(request)
    if (
        invitation is None
        or invitation.existing_user_id is not None
        or invitation.invitation_type
        not in {InvitationType.NEW_USER, InvitationType.INITIAL_OWNER}
    ):
        return None
    return invitation


@transaction.atomic
def accept_session_invitation(*, request: HttpRequest, user: User) -> Membership | None:
    invitation = _session_invitation(request, require_available=False)
    if invitation is None:
        return None
    locked = (
        MembershipInvitation.objects.select_for_update(of=("self",))
        .select_related("organization", "existing_user")
        .get(pk=invitation.pk)
    )
    if locked.email.lower() != user.email.lower():
        raise InvitationUnavailable("La invitación no corresponde a esta cuenta.")
    if locked.existing_user_id and locked.existing_user_id != user.pk:
        raise InvitationUnavailable("La invitación no corresponde a esta cuenta.")
    if not EmailAddress.objects.filter(
        user=user, email__iexact=user.email, verified=True
    ).exists():
        raise VerifiedUserRequired("Debes verificar el correo antes de aceptar.")
    if locked.status == InvitationStatus.ACCEPTED:
        membership = (
            Membership.objects.filter(
                organization=locked.organization,
                user=user,
            )
            .exclude(status=MembershipStatus.REVOKED)
            .first()
        )
        if membership is None:
            raise InvitationUnavailable("La invitación no está disponible.")
        request.session.pop("organization_invitation_id", None)
        request.session.pop("organization_invitation_digest", None)
        return membership
    _assert_invitation_available(locked)
    if (
        locked.organization.status == OrganizationStatus.PENDING_ACTIVATION
        and locked.invitation_type != InvitationType.INITIAL_OWNER
    ):
        raise InvitationUnavailable(
            "La persona propietaria debe activar primero la institución."
        )
    membership = _create_active_membership(
        organization=locked.organization,
        user=user,
        actor=user,
        roles={RoleCode(role) for role in locked.invited_roles},
        invitation=locked,
    )
    if locked.invitation_type == InvitationType.INITIAL_OWNER:
        organization = Organization.objects.select_for_update().get(
            pk=locked.organization_id
        )
        if organization.status != OrganizationStatus.PENDING_ACTIVATION:
            raise InvitationUnavailable("La institución ya fue activada.")
        organization.status = OrganizationStatus.ACTIVE
        organization.activated_at = timezone.now()
        organization.full_clean()
        organization.save(update_fields=("status", "activated_at", "updated_at"))
    locked.status = InvitationStatus.ACCEPTED
    locked.accepted_at = timezone.now()
    locked.save(update_fields=("status", "accepted_at", "updated_at"))
    request.session.pop("organization_invitation_id", None)
    request.session.pop("organization_invitation_digest", None)
    _record_event(
        organization=locked.organization,
        membership=membership,
        actor=user,
        event_type=MembershipEventType.INVITATION_ACCEPTED,
        details={"invitation_type": locked.invitation_type},
    )
    return membership


def complete_onboarding_after_email_verification(
    *, request: HttpRequest, user: User
) -> None:
    invitation = _session_invitation(request)
    if invitation and invitation.invitation_type in {
        InvitationType.NEW_USER,
        InvitationType.INITIAL_OWNER,
    }:
        accept_session_invitation(request=request, user=user)
    join_slug = request.session.pop("organization_join_slug", None)
    if isinstance(join_slug, str):
        organization = Organization.objects.filter(slug=join_slug).first()
        if organization is not None:
            create_public_join_request(user=user, organization=organization)


@transaction.atomic
def activate_managed_account(*, request: HttpRequest, password: str) -> Membership:
    invitation = _session_invitation(request)
    if (
        invitation is None
        or invitation.invitation_type != InvitationType.MANAGED_ACCOUNT
    ):
        raise InvitationUnavailable("La activación no está disponible.")
    locked = (
        MembershipInvitation.objects.select_for_update(of=("self",))
        .select_related("existing_user", "organization")
        .get(pk=invitation.pk)
    )
    _assert_invitation_available(locked)
    if locked.existing_user is None:
        raise InvitationUnavailable("La activación no está disponible.")
    user = locked.existing_user
    user.set_password(password)
    user.is_active = True
    user.save(update_fields=("password", "is_active"))
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={"primary": True, "verified": True},
    )
    membership = _create_active_membership(
        organization=locked.organization,
        user=user,
        actor=user,
        roles={RoleCode(role) for role in locked.invited_roles},
        invitation=locked,
    )
    locked.status = InvitationStatus.ACCEPTED
    locked.accepted_at = timezone.now()
    locked.save(update_fields=("status", "accepted_at", "updated_at"))
    request.session.pop("organization_invitation_id", None)
    request.session.pop("organization_invitation_digest", None)
    _record_event(
        organization=locked.organization,
        membership=membership,
        actor=user,
        event_type=MembershipEventType.MANAGED_ACCOUNT_ACTIVATED,
    )
    return membership


@transaction.atomic
def manually_activate_managed_account(
    *,
    actor: User,
    invitation: MembershipInvitation,
    temporary_password: str,
    confirm_identity: bool,
) -> Membership:
    """Activate an institution-managed account after an in-person identity check."""

    locked = (
        MembershipInvitation.objects.select_for_update(of=("self",))
        .select_related("existing_user", "organization")
        .get(pk=invitation.pk)
    )
    _require_capability(
        actor, locked.organization, Capability.MEMBERSHIP_INVITATION_MANAGE
    )
    _assert_invitation_available(locked)
    if not confirm_identity:
        raise InvitationUnavailable(
            "Confirma que la institución verificó presencialmente la identidad."
        )
    if (
        locked.invitation_type != InvitationType.MANAGED_ACCOUNT
        or locked.existing_user is None
    ):
        raise InvitationUnavailable(
            "Sólo las cuentas administradas pueden activarse manualmente."
        )
    user = locked.existing_user
    validate_password(temporary_password, user=user)
    user.set_password(temporary_password)
    user.is_active = True
    user.save(update_fields=("password", "is_active"))
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={"primary": True, "verified": True},
    )
    membership = _create_active_membership(
        organization=locked.organization,
        user=user,
        actor=actor,
        roles={RoleCode(role) for role in locked.invited_roles},
        invitation=locked,
    )
    locked.status = InvitationStatus.ACCEPTED
    locked.accepted_at = timezone.now()
    locked.save(update_fields=("status", "accepted_at", "updated_at"))
    _record_event(
        organization=locked.organization,
        membership=membership,
        actor=actor,
        event_type=MembershipEventType.MANAGED_ACCOUNT_ACTIVATED,
        details={"activation_method": "administrator_identity_check"},
    )
    return membership


def begin_public_join(*, request: HttpRequest, organization: Organization) -> None:
    settings = OrganizationMembershipSettings.objects.get(organization=organization)
    if not settings.public_join_enabled:
        raise JoinRequestUnavailable("Esta institución no acepta solicitudes públicas.")
    request.session["organization_join_slug"] = organization.slug
    request.session.modified = True


def _email_domain_allowed(
    *, email: str, settings: OrganizationMembershipSettings
) -> bool:
    if not settings.allowed_email_domains:
        return True
    domain = email.rpartition("@")[2].lower()
    return domain in set(settings.allowed_email_domains)


@transaction.atomic
def create_public_join_request(
    *, user: User, organization: Organization
) -> OrganizationJoinRequest | Membership:
    settings = _locked_membership_settings(organization)
    if not settings.public_join_enabled or not _email_domain_allowed(
        email=user.email, settings=settings
    ):
        raise JoinRequestUnavailable("La solicitud no está disponible.")
    if (
        Membership.objects.filter(organization=organization, user=user)
        .exclude(status=MembershipStatus.REVOKED)
        .exists()
    ):
        raise MemberAlreadyExists("La persona ya tiene una membresía vigente.")
    if not settings.join_requires_approval:
        return _create_active_membership(
            organization=organization,
            user=user,
            actor=None,
            roles={RoleCode(settings.default_role)},
        )
    try:
        request = OrganizationJoinRequest.objects.create(
            organization=organization, user=user, email=user.email.lower()
        )
    except IntegrityError as error:
        raise JoinRequestAlreadyExists("Ya existe una solicitud pendiente.") from error
    _record_event(
        organization=organization,
        membership=None,
        actor=user,
        event_type=MembershipEventType.JOIN_REQUESTED,
    )
    return request


@transaction.atomic
def review_join_request(
    *, actor: User, join_request: OrganizationJoinRequest, approve: bool
) -> OrganizationJoinRequest:
    locked = (
        OrganizationJoinRequest.objects.select_for_update()
        .select_related("organization", "user")
        .get(pk=join_request.pk)
    )
    _require_capability(
        actor, locked.organization, Capability.MEMBERSHIP_JOIN_REQUEST_MANAGE
    )
    if locked.status != JoinRequestStatus.PENDING:
        raise JoinRequestUnavailable("La solicitud ya fue resuelta.")
    locked.status = (
        JoinRequestStatus.APPROVED if approve else JoinRequestStatus.REJECTED
    )
    locked.reviewed_by = actor
    locked.reviewed_at = timezone.now()
    locked.save(update_fields=("status", "reviewed_by", "reviewed_at", "updated_at"))
    membership = None
    if approve:
        role = RoleCode(_locked_membership_settings(locked.organization).default_role)
        membership = _create_active_membership(
            organization=locked.organization,
            user=locked.user,
            actor=actor,
            roles={role},
        )
    _record_event(
        organization=locked.organization,
        membership=membership,
        actor=actor,
        event_type=(
            MembershipEventType.JOIN_APPROVED
            if approve
            else MembershipEventType.JOIN_REJECTED
        ),
    )
    return locked


@transaction.atomic
def update_member_profile(
    *,
    actor: User,
    membership: Membership,
    member_type: str,
    institutional_id: str,
    preferred_name: str,
    phone: str,
    locale: str,
    timezone_name: str,
    administrative_notes: str | None = None,
    profile_values: dict[str, object] | None = None,
) -> OrganizationMemberProfile:
    locked = _locked_membership(membership)
    is_self = locked.user_id == actor.pk
    can_manage = has_capability(
        actor, locked.organization, Capability.MEMBERSHIP_PROFILE_MANAGE
    )
    if not is_self and not can_manage:
        _require_capability(
            actor, locked.organization, Capability.MEMBERSHIP_PROFILE_MANAGE
        )
    profile, _ = OrganizationMemberProfile.objects.select_for_update().get_or_create(
        membership=locked
    )
    if (
        is_self
        and not can_manage
        and (
            member_type != profile.member_type
            or institutional_id != profile.institutional_id
            or administrative_notes is not None
        )
    ):
        raise OrganizationAccessDenied(
            "Solo la institución puede modificar los datos administrativos."
        )
    profile.member_type = normalize_member_type(member_type)
    profile.institutional_id = institutional_id.strip()
    profile.preferred_name = preferred_name.strip()
    profile.phone = phone.strip()
    profile.locale = locale.strip() or "es"
    profile.timezone = timezone_name.strip() or "UTC"
    editable_fields = {
        "first_name",
        "middle_name",
        "first_surname",
        "second_surname",
        "whatsapp",
        "date_of_birth",
        "document_type",
        "document_number",
        "gender",
        "education_stage",
        "education_institution",
        "education_level",
        "department_code",
        "municipality",
        "address",
        "socioeconomic_stratum",
        "registration_reason",
        "registration_reason_detail",
    }
    for field_name, raw_value in (profile_values or {}).items():
        if field_name not in editable_fields:
            continue
        value = raw_value.strip() if isinstance(raw_value, str) else raw_value
        setattr(profile, field_name, value)
    if administrative_notes is not None:
        if not can_manage:
            raise OrganizationAccessDenied(
                "No puedes modificar las notas administrativas."
            )
        profile.administrative_notes = administrative_notes.strip()
    profile.full_clean()
    profile.save()
    _record_event(
        organization=locked.organization,
        membership=locked,
        actor=actor,
        event_type=MembershipEventType.PROFILE_UPDATED,
    )
    return profile


@transaction.atomic
def revoke_user_sessions(*, actor: User, membership: Membership) -> int:
    locked = _locked_membership(membership)
    _require_capability(
        actor, locked.organization, Capability.MEMBERSHIP_SESSIONS_REVOKE
    )
    deleted = 0
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        if session.get_decoded().get("_auth_user_id") == str(locked.user_id):
            session.delete()
            deleted += 1
    _record_event(
        organization=locked.organization,
        membership=locked,
        actor=actor,
        event_type=MembershipEventType.SESSIONS_REVOKED,
    )
    return deleted


@transaction.atomic
def send_member_password_recovery(*, actor: User, membership: Membership) -> None:
    """Send recovery instructions without binding a flow to the administrator session."""

    locked = _locked_membership(membership)
    _require_capability(actor, locked.organization, Capability.MEMBERSHIP_RECOVERY_SEND)
    if locked.status != MembershipStatus.ACTIVE.value or not locked.user.is_active:
        raise MembershipNotActive(
            "La recuperación solo está disponible para cuentas activas."
        )
    event = _record_event(
        organization=locked.organization,
        membership=locked,
        actor=actor,
        event_type=MembershipEventType.PASSWORD_RECOVERY_SENT,
    )
    transaction.on_commit(
        lambda: _send_member_recovery_email(
            membership=locked,
            event_id=str(event.pk),
        )
    )
