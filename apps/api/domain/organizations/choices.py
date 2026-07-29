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
