from django.db import models


class RoleCode(models.TextChoices):
    OWNER = "owner", "Propietario"
    ADMINISTRATOR = "administrator", "Administrador"
    AUTHOR = "author", "Autor"
    REVIEWER = "reviewer", "Revisor"
    INSTRUCTOR = "instructor", "Docente"
    LEARNER = "learner", "Estudiante"


class MembershipStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    SUSPENDED = "suspended", "Suspendida"
    REVOKED = "revoked", "Revocada"


class MembershipEventType(models.TextChoices):
    CREATED = "membership_created", "Membresía creada"
    SUSPENDED = "membership_suspended", "Membresía suspendida"
    REACTIVATED = "membership_reactivated", "Membresía reactivada"
    REVOKED = "membership_revoked", "Membresía revocada"
    ROLE_ASSIGNED = "role_assigned", "Rol asignado"
    ROLE_REVOKED = "role_revoked", "Rol revocado"
    INVITATION_CREATED = "invitation_created", "Invitación creada"
    INVITATION_UPDATED = "invitation_updated", "Invitación actualizada"
    INVITATION_RESENT = "invitation_resent", "Invitación reenviada"
    INVITATION_REVOKED = "invitation_revoked", "Invitación revocada"
    INVITATION_ACCEPTED = "invitation_accepted", "Invitación aceptada"
    JOIN_REQUESTED = "join_requested", "Solicitud de ingreso creada"
    JOIN_APPROVED = "join_approved", "Solicitud de ingreso aprobada"
    JOIN_REJECTED = "join_rejected", "Solicitud de ingreso rechazada"
    MANAGED_ACCOUNT_CREATED = "managed_account_created", "Cuenta administrada creada"
    MANAGED_ACCOUNT_ACTIVATED = (
        "managed_account_activated",
        "Cuenta administrada activada",
    )
    PROFILE_UPDATED = "profile_updated", "Perfil institucional actualizado"
    ROLES_REPLACED = "roles_replaced", "Roles sustituidos"
    SESSIONS_REVOKED = "sessions_revoked", "Sesiones revocadas"
    SETTINGS_UPDATED = (
        "membership_settings_updated",
        "Configuración de membresías actualizada",
    )


class InvitationType(models.TextChoices):
    EXISTING_USER = "existing_user", "Usuario existente"
    NEW_USER = "new_user", "Usuario nuevo"
    MANAGED_ACCOUNT = "managed_account", "Cuenta administrada"


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    ACCEPTED = "accepted", "Aceptada"
    REVOKED = "revoked", "Revocada"
    EXPIRED = "expired", "Expirada"


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    APPROVED = "approved", "Aprobada"
    REJECTED = "rejected", "Rechazada"
    CANCELLED = "cancelled", "Cancelada"
